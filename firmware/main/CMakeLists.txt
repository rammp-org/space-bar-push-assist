idf_component_register(
  SRC_DIRS "."
  INCLUDE_DIRS "."
  REQUIRES hx711 base_component format logger telemetry dispatcher stream_frame task coredump
           ethernet esp_app_format esp_driver_tsens lwip espcoredump)
