# Proximity Dither (Fabric 1.20.1)

Recria o **Camera Proximity Dithering** do Bedrock: quando uma entidade (mob, jogador, armadura, capa...) chega perto da câmera, os pixels dela somem num padrão de pontos (Bayer 4x4) em vez de tampar a tela.

Todo o efeito está nos *core shaders* em `src/main/resources/assets/minecraft/shaders/core/`. O código Java é só o ponto de entrada.

## Testar rápido (sem compilar)

O zip `proximity-dither-resourcepack.zip` é um resource pack com os mesmos shaders. Coloque em `.minecraft/resourcepacks/`, ative no jogo e pronto.

## Compilar o mod

Precisa de JDK 17 e internet na primeira vez.

```
gradle wrapper --gradle-version 8.5
./gradlew build
```

O `.jar` sai em `build/libs/` (use o que **não** termina em `-sources`). Coloque na pasta `mods/` do Fabric Loader 0.14.21+ com Minecraft 1.20.1. Não precisa do Fabric API.

## Ajustar as distâncias

```
python3 tools/generate_shaders.py --near 0.5 --far 2.5
```

- `near`: abaixo disso (em blocos) a entidade some por completo. Padrão `0.35`.
- `far`: a partir daqui a entidade fica totalmente visível. Padrão `1.5`.

O script regera os `.json/.vsh/.fsh`. Depois é só recompilar (ou recriar o zip do resource pack).

## Como funciona

1. O vertex shader manda a posição do pixel no espaço da câmera para o fragment shader.
2. O fragment shader calcula a distância até a câmera e converte em visibilidade (0 a 1) com `smoothstep(near, far, distância)`.
3. Compara a visibilidade com um limiar da matriz Bayer 4x4, indexada por `gl_FragCoord`. Se a visibilidade for menor, o pixel é descartado.
4. O resto (textura, luz, overlay de dano, névoa) segue a mesma ordem do vanilla.

A mão em primeira pessoa e os itens da GUI ficam de fora: nesses casos o jogo deixa `FogStart` gigante, e o shader pula o dithering.

## Programas cobertos

`rendertype_entity_cutout`, `rendertype_entity_cutout_no_cull`, `rendertype_entity_solid`, `rendertype_entity_translucent` e `rendertype_armor_cutout_no_cull`. Isso cobre mobs, jogador, armaduras e capas.

## Limitações conhecidas

- **Não foi compilado nem testado no jogo.** Foi escrito sem acesso aos shaders originais do vanilla, então pode precisar de ajuste.
- Não cobre olhos de aranha/Enderman (`rendertype_eyes`), brilho de encantamento, `entity_translucent_cull`, itens caídos translúcidos nem `entity_cutout_no_cull_z_offset`. Esses podem ficar visíveis enquanto o corpo some.
- Não funciona com shader packs do Iris/Optifine ativos, que substituem esses programas.
- Outros mods ou resource packs que substituem os mesmos arquivos em `assets/minecraft/shaders/core/` entram em conflito.
