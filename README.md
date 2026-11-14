# Proximity Dither

Porta pro Fabric 1.20.1 do dithering de proximidade da câmera do Bedrock. Quando um mob, jogador ou armadura chega muito perto da câmera, em vez de tampar a tela ele vai sumindo em pontinhos (padrão Bayer 4x4).

Funciona só com core shaders. Os shaders vêm dentro do próprio jar e já entram ativos quando o mod carrega, não precisa ligar resource pack nenhum.

## Instalar

Pega o `.jar` nos artifacts do Actions (ou compila, abaixo) e joga em `mods/`. Precisa de Minecraft 1.20.1, Fabric Loader 0.14.21 ou mais novo e o [Fabric API](https://modrinth.com/mod/fabric-api) (é ele que carrega os shaders do mod).

Se quiser só testar o efeito sem o mod, o mesmo conteúdo sai como resource pack (`proximity-dither-resourcepack.zip`, também nos artifacts). Não use o pack junto com o mod, é redundante.

## Compilar

JDK 17.

```
gradle wrapper --gradle-version 8.5
./gradlew build
```

O jar fica em `build/libs/` (o que não termina em `-sources`).

## Distâncias

Os shaders são gerados por `tools/generate_shaders.py`, então não edite os `.vsh/.fsh` na mão:

```
python3 tools/generate_shaders.py --near 0.5 --far 2.5
```

`near` é onde some de vez (padrão 0.35 blocos) e `far` é onde volta ao normal (padrão 1.5).

## O que cobre

`entity_cutout`, `entity_cutout_no_cull`, `entity_solid`, `entity_translucent` e `armor_cutout_no_cull`. Dá conta de mobs, jogador, armadura e capa. Mão em primeira pessoa e itens de GUI ficam de fora.

## Problemas conhecidos

- Ainda pouco testado, então pode ter bug.
- Olhos de aranha/Enderman, brilho de encantamento e itens caídos translúcidos não entram, e podem ficar visíveis enquanto o resto some.
- Não combina com Iris/Optifine com shader pack ligado, nem com outro mod ou pack que troque os mesmos arquivos de `shaders/core`.
