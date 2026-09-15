# CMakeLists.txt for Keyboardio Preonic Module

if(CONFIG_KEYBOARDIO_BUTTERFLY_STATUS)
    target_sources_ifdef(CONFIG_KEYBOARDIO_BUTTERFLY_STATUS app PRIVATE
        src/butterfly_status.c
        src/battery_typer.c
        src/dynamic_macro.c
        src/password_generator.c
    )
    zephyr_include_directories(include)
endif()

if(CONFIG_KEYBOARDIO_PREONIC_SOUND)
    target_sources_ifdef(CONFIG_KEYBOARDIO_PREONIC_SOUND app PRIVATE src/preonic_sound.c)
    zephyr_include_directories(include)
endif()

if(CONFIG_KEYBOARDIO_PREONIC_STUDIO)
    target_sources_ifdef(CONFIG_KEYBOARDIO_PREONIC_STUDIO app PRIVATE src/preonic_studio.c)
    zephyr_include_directories(include)
endif()
