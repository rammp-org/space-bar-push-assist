#pragma once

// EthLink: the espp framed service stream over the board's ethernet. Adapted
// from PACE RACER's atos-drive EthLink (pace-racer-fw, main/eth_link.hpp),
// without its OTA, console and rollback parts.
//
//   TCP :5555   one espp stream_frame byte stream, one client at a time (a
//               newcomer replaces a stale session), routed by an
//               espp::DispatcherWorker to whatever modules the app registers.
//   UDP :5556   "PUSH?" in (broadcast or unicast) -> one JSON line back,
//               unicast to the asker. Host-initiated on purpose: a unicast
//               reply to a broadcast question gets through switches that eat
//               device-originated multicast.
//
// All socket work runs on one task: a select() loop over the listen socket,
// the client and the UDP responder. Frames from any thread go out through one
// mutex with a short send timeout, so a stalled client cannot hold up the
// sample loop for long.

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cstring>
#include <functional>
#include <memory>
#include <mutex>
#include <span>
#include <string>

#include "lwip/sockets.h"

#include "dispatcher_worker.hpp"
#include "logger.hpp"
#include "task.hpp"

class EthLink {
public:
  struct Config {
    uint16_t port{5555};           ///< TCP service port.
    uint16_t discovery_port{5556}; ///< UDP "PUSH?" responder; 0 disables.
    std::string product;           ///< Discovery device name.
    std::string firmware;          ///< Firmware version for discovery.
    /// JSON object for the UDP discovery reply.
    std::function<std::string()> info_json{nullptr};
    /// Called on the server task when a client connects.
    std::function<void()> on_connect{nullptr};
    /// Called on the server task when the client goes away.
    std::function<void()> on_disconnect{nullptr};
    espp::Logger::Verbosity log_level{espp::Logger::Verbosity::INFO};
  };

  explicit EthLink(const Config &cfg)
      : cfg_(cfg)
      , logger_({.tag = "EthLink", .level = cfg.log_level})
      , worker_({.send = [this](std::span<const uint8_t> f) { send(f); },
                 .task_config = {.name = "eth_rx", .stack_size_bytes = 8192}}) {}

  ~EthLink() { stop(); }
  EthLink(const EthLink &) = delete;
  EthLink &operator=(const EthLink &) = delete;

  /// Register modules here before start().
  espp::DispatcherWorker &worker() { return worker_; }

  /// Open the sockets and start the server task. Needs the TCP/IP stack up
  /// (the BSP's initialize_ethernet); a lease is not needed, 0.0.0.0 listens.
  bool start() {
    worker_.serve_discovery(cfg_.product, cfg_.firmware);
    listen_fd_ = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_fd_ < 0) {
      logger_.error("socket() failed: {}", errno);
      return false;
    }
    int one = 1;
    ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(cfg_.port);
    if (::bind(listen_fd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0 ||
        ::listen(listen_fd_, 1) < 0) {
      logger_.error("bind/listen on :{} failed: {}", cfg_.port, errno);
      ::close(listen_fd_);
      listen_fd_ = -1;
      return false;
    }
    if (cfg_.discovery_port) {
      udp_fd_ = ::socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
      if (udp_fd_ >= 0) {
        ::setsockopt(udp_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
        sockaddr_in u{};
        u.sin_family = AF_INET;
        u.sin_addr.s_addr = htonl(INADDR_ANY);
        u.sin_port = htons(cfg_.discovery_port);
        if (::bind(udp_fd_, reinterpret_cast<sockaddr *>(&u), sizeof(u)) < 0) {
          logger_.error("discovery bind on :{} failed: {}", cfg_.discovery_port, errno);
          ::close(udp_fd_);
          udp_fd_ = -1;
        }
      }
    }
    running_.store(true);
    task_ = espp::Task::make_unique(espp::Task::Config{
        .callback = [this](std::mutex &m, std::condition_variable &cv) { return serve(m, cv); },
        .task_config = {.name = "eth_link", .stack_size_bytes = 6 * 1024, .priority = 4},
        .log_level = espp::Logger::Verbosity::WARN,
    });
    task_->start();
    logger_.info("service stream on tcp :{}, discovery on udp :{}", cfg_.port,
                 udp_fd_ >= 0 ? cfg_.discovery_port : 0);
    return true;
  }

  void stop() {
    running_.store(false);
    if (task_) {
      task_->stop();
      task_.reset();
    }
    close_client();
    if (listen_fd_ >= 0) {
      ::close(listen_fd_);
      listen_fd_ = -1;
    }
    if (udp_fd_ >= 0) {
      ::close(udp_fd_);
      udp_fd_ = -1;
    }
  }

  bool client_connected() const { return client_fd_.load() >= 0; }

  /// Write one frame to the client (any thread). Dropped with no client; a
  /// failed write drops the client.
  void send(std::span<const uint8_t> f) {
    const int fd = client_fd_.load();
    if (fd < 0)
      return;
    std::lock_guard<std::mutex> lk(send_mutex_);
    size_t off = 0;
    while (off < f.size()) {
      const int w = ::send(fd, f.data() + off, f.size() - off, 0);
      if (w <= 0) {
        logger_.warn("send failed ({}), dropping client", errno);
        // close_client() takes send_mutex_, so the server task closes it.
        client_lost_.store(true);
        return;
      }
      off += static_cast<size_t>(w);
    }
  }

protected:
  static constexpr size_t kRxChunk = 2048;

  bool serve(std::mutex &, std::condition_variable &) {
    if (!running_.load())
      return true;
    if (client_lost_.exchange(false))
      close_client();
    fd_set rfds;
    FD_ZERO(&rfds);
    int maxfd = -1;
    auto add = [&](int fd) {
      if (fd >= 0) {
        FD_SET(fd, &rfds);
        maxfd = std::max(maxfd, fd);
      }
    };
    add(listen_fd_);
    add(udp_fd_);
    const int client = client_fd_.load();
    add(client);
    timeval tv{.tv_sec = 0, .tv_usec = 50 * 1000};
    const int n = ::select(maxfd + 1, &rfds, nullptr, nullptr, &tv);
    if (n > 0) {
      if (listen_fd_ >= 0 && FD_ISSET(listen_fd_, &rfds))
        accept_client();
      if (udp_fd_ >= 0 && FD_ISSET(udp_fd_, &rfds))
        answer_discovery();
      if (client >= 0 && FD_ISSET(client, &rfds))
        read_client(client);
    }
    return false;
  }

  void accept_client() {
    sockaddr_in peer{};
    socklen_t len = sizeof(peer);
    const int fd = ::accept(listen_fd_, reinterpret_cast<sockaddr *>(&peer), &len);
    if (fd < 0)
      return;
    close_client();
    int one = 1;
    ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
    timeval snd{.tv_sec = 0, .tv_usec = 300 * 1000};
    ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &snd, sizeof(snd));
    char ip[16] = "?";
    inet_ntoa_r(peer.sin_addr, ip, sizeof(ip));
    worker_.request_reset();
    client_fd_.store(fd);
    logger_.info("client {}:{} connected", ip, ntohs(peer.sin_port));
    if (cfg_.on_connect)
      cfg_.on_connect();
  }

  void read_client(int fd) {
    uint8_t buf[kRxChunk];
    const int r = ::recv(fd, buf, sizeof(buf), 0);
    if (r <= 0) {
      logger_.info("client gone ({})", r == 0 ? "closed" : "error");
      close_client();
      return;
    }
    worker_.push(std::span<const uint8_t>(buf, static_cast<size_t>(r)));
  }

  void close_client() {
    const int fd = client_fd_.exchange(-1);
    if (fd < 0)
      return;
    {
      std::lock_guard<std::mutex> lk(send_mutex_);
      ::shutdown(fd, SHUT_RDWR);
      ::close(fd);
    }
    if (cfg_.on_disconnect)
      cfg_.on_disconnect();
  }

  void answer_discovery() {
    char buf[64];
    sockaddr_in from{};
    socklen_t len = sizeof(from);
    const int r =
        ::recvfrom(udp_fd_, buf, sizeof(buf) - 1, 0, reinterpret_cast<sockaddr *>(&from), &len);
    if (r <= 0)
      return;
    buf[r] = 0;
    if (std::strncmp(buf, "PUSH?", 5) != 0)
      return;
    const std::string reply = cfg_.info_json ? cfg_.info_json() : "{}";
    ::sendto(udp_fd_, reply.data(), reply.size(), 0, reinterpret_cast<sockaddr *>(&from), len);
  }

  Config cfg_;
  espp::Logger logger_;
  espp::DispatcherWorker worker_;
  std::unique_ptr<espp::Task> task_;
  std::atomic<bool> running_{false};
  std::atomic<bool> client_lost_{false};
  std::atomic<int> client_fd_{-1};
  std::mutex send_mutex_;
  int listen_fd_{-1};
  int udp_fd_{-1};
};
