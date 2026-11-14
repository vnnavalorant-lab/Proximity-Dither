package com.proximitydither;

import net.fabricmc.api.ClientModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

// All the work is done by the core shaders, nothing to hook into yet.
public class ProximityDitherClient implements ClientModInitializer {
    public static final String MOD_ID = "proximitydither";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitializeClient() {
        LOGGER.info("Proximity Dither loaded");
    }
}
