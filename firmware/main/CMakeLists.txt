idf_component_register(
  SRC_DIRS "."
  INCLUDE_DIRS "."
  REQUIRES hx711 base_component format logger telemetry dispatcher stream_frame task coredump
           ethernet ota rtps rammp_rtps_messages esp_app_format esp_driver_tsens lwip nvs_flash
           app_update espcoredump)
