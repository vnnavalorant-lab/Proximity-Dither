package com.proximitydither;

import net.fabricmc.api.ClientModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * O efeito inteiro vive nos core shaders em
 * assets/minecraft/shaders/core/ (rendertype_entity_*). Esta classe existe so
 * como ponto de entrada para futuras extensoes (config, atalho de teclado etc.).
 */
public class ProximityDitherClient implements ClientModInitializer {
    public static final String MOD_ID = "proximitydither";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitializeClient() {
        LOGGER.info("Proximity Dither carregado: entidades perto da camera usam dithering.");
    }
}
