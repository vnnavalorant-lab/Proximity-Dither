#!/usr/bin/env python3
"""Gera os shaders do Proximity Dither (json + vsh + fsh) para o Minecraft 1.20.1.

Uso:
    python3 tools/generate_shaders.py                  # padrao: near=0.35, far=1.5
    python3 tools/generate_shaders.py --near 0.5 --far 2.5

near = distancia (em blocos) abaixo da qual a entidade fica totalmente invisivel
far  = distancia a partir da qual a entidade fica totalmente visivel
Entre as duas, o numero de pixels descartados cai gradualmente (padrao Bayer 4x4).
"""
import argparse
import json
from pathlib import Path

IDENT3 = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
IDENT4 = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]

# programa -> (descarta alpha baixo?, usa blend translucido?)
VARIANTS = {
    "rendertype_entity_cutout_no_cull": (True, False),
    "rendertype_entity_cutout": (True, False),
    "rendertype_entity_solid": (False, False),
    "rendertype_entity_translucent": (True, True),
    "rendertype_armor_cutout_no_cull": (True, False),
}

VSH = """#version 150

// Proximity Dither - vertex shader (formato de vertice de entidade).
// Gerado por tools/generate_shaders.py. Edite o script, nao este arquivo.

#define MINECRAFT_LIGHT_POWER   (0.6)
#define MINECRAFT_AMBIENT_LIGHT (0.4)

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;

uniform sampler2D Sampler1;
uniform sampler2D Sampler2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform mat3 IViewRotMat;
uniform int FogShape;

uniform vec3 Light0_Direction;
uniform vec3 Light1_Direction;

out float vertexDistance;
out vec3 viewPos;
out vec4 vertexColor;
out vec4 lightMapColor;
out vec4 overlayColor;
out vec2 texCoord0;

vec4 dither_mix_light(vec3 lightDir0, vec3 lightDir1, vec3 normal, vec4 color) {
    lightDir0 = normalize(lightDir0);
    lightDir1 = normalize(lightDir1);
    float light0 = max(0.0, dot(lightDir0, normal));
    float light1 = max(0.0, dot(lightDir1, normal));
    float lightAccum = min(1.0, (light0 + light1) * MINECRAFT_LIGHT_POWER + MINECRAFT_AMBIENT_LIGHT);
    return vec4(color.rgb * lightAccum, color.a);
}

float dither_fog_distance(mat4 modelViewMat, vec3 pos, int shape) {
    if (shape == 0) {
        return length((modelViewMat * vec4(pos, 1.0)).xyz);
    }
    float distXZ = length((modelViewMat * vec4(pos.x, 0.0, pos.z, 1.0)).xyz);
    float distY = length((modelViewMat * vec4(0.0, pos.y, 0.0, 1.0)).xyz);
    return max(distXZ, distY);
}

void main() {
    vec4 viewPosition = ModelViewMat * vec4(Position, 1.0);
    gl_Position = ProjMat * viewPosition;

    vertexDistance = dither_fog_distance(ModelViewMat, IViewRotMat * Position, FogShape);
    viewPos = viewPosition.xyz;
    vertexColor = dither_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
    lightMapColor = texelFetch(Sampler2, UV2 / 16, 0);
    overlayColor = texelFetch(Sampler1, UV1, 0);
    texCoord0 = UV0;
}
"""

FSH = """#version 150

// Proximity Dither - fragment shader.
// Inspirado no "Camera Proximity Dithering" do Minecraft Bedrock: perto da camera,
// pixels da entidade sao descartados num padrao Bayer 4x4 fixo na tela.
// Gerado por tools/generate_shaders.py. Edite o script, nao este arquivo.

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec3 viewPos;
in vec4 vertexColor;
in vec4 lightMapColor;
in vec4 overlayColor;
in vec2 texCoord0;

out vec4 fragColor;

// Distancias em blocos, medidas da camera ate o pixel.
const float DITHER_NEAR = @NEAR@; // abaixo disso: totalmente invisivel
const float DITHER_FAR = @FAR@;   // acima disso: totalmente visivel

const float BAYER4[16] = float[16](
     0.0,  8.0,  2.0, 10.0,
    12.0,  4.0, 14.0,  6.0,
     3.0, 11.0,  1.0,  9.0,
    15.0,  7.0, 13.0,  5.0
);

vec4 dither_linear_fog(vec4 inColor, float dist, float fogStart, float fogEnd, vec4 fogColor) {
    if (dist <= fogStart) {
        return inColor;
    }
    float fogValue = dist < fogEnd ? smoothstep(fogStart, fogEnd, dist) : 1.0;
    return vec4(mix(inColor.rgb, fogColor.rgb, fogValue * fogColor.a), inColor.a);
}

void main() {
    // Fora do mundo (mao em primeira pessoa, GUI) o jogo deixa FogStart gigante.
    // Nesses casos o dithering nao e aplicado.
    float camDist = length(viewPos);
    if (FogStart < 1.0e6 && camDist < DITHER_FAR) {
        float visibility = smoothstep(DITHER_NEAR, DITHER_FAR, camDist);
        ivec2 cell = ivec2(mod(gl_FragCoord.xy, 4.0));
        float threshold = (BAYER4[cell.y * 4 + cell.x] + 0.5) / 16.0;
        if (visibility <= threshold) {
            discard;
        }
    }

    vec4 color = texture(Sampler0, texCoord0) * vertexColor;
@ALPHA@    color *= ColorModulator;
    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
    color *= lightMapColor;
    fragColor = dither_linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
"""

ALPHA_TEST = "    if (color.a < 0.1) {\n        discard;\n    }\n"


def make_json(name: str, translucent: bool) -> dict:
    data = {}
    if translucent:
        data["blend"] = {"func": "add", "srcrgb": "srcalpha", "dstrgb": "1-srcalpha"}
    data["vertex"] = name
    data["fragment"] = name
    data["samplers"] = [{"name": "Sampler0"}, {"name": "Sampler1"}, {"name": "Sampler2"}]
    data["uniforms"] = [
        {"name": "ModelViewMat", "type": "matrix4x4", "count": 16, "values": IDENT4},
        {"name": "ProjMat", "type": "matrix4x4", "count": 16, "values": IDENT4},
        {"name": "IViewRotMat", "type": "matrix3x3", "count": 9, "values": IDENT3},
        {"name": "ColorModulator", "type": "float", "count": 4, "values": [1.0, 1.0, 1.0, 1.0]},
        {"name": "Light0_Direction", "type": "float", "count": 3, "values": [0.0, 0.0, 0.0]},
        {"name": "Light1_Direction", "type": "float", "count": 3, "values": [0.0, 0.0, 0.0]},
        {"name": "FogStart", "type": "float", "count": 1, "values": [0.0]},
        {"name": "FogEnd", "type": "float", "count": 1, "values": [1.0]},
        {"name": "FogColor", "type": "float", "count": 4, "values": [0.0, 0.0, 0.0, 0.0]},
        {"name": "FogShape", "type": "int", "count": 1, "values": [0]},
    ]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--near", type=float, default=0.35)
    parser.add_argument("--far", type=float, default=1.5)
    args = parser.parse_args()
    if not 0.0 <= args.near < args.far:
        parser.error("e preciso ter 0 <= near < far")

    out_dir = Path(__file__).resolve().parent.parent / "src/main/resources/assets/minecraft/shaders/core"
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, (alpha_test, translucent) in VARIANTS.items():
        fsh = (
            FSH.replace("@NEAR@", repr(float(args.near)))
            .replace("@FAR@", repr(float(args.far)))
            .replace("@ALPHA@", ALPHA_TEST if alpha_test else "")
        )
        (out_dir / f"{name}.vsh").write_text(VSH, encoding="ascii")
        (out_dir / f"{name}.fsh").write_text(fsh, encoding="ascii")
        (out_dir / f"{name}.json").write_text(json.dumps(make_json(name, translucent), indent=4) + "\n", encoding="ascii")

    print(f"{len(VARIANTS)} programas gerados em {out_dir} (near={args.near}, far={args.far})")


if __name__ == "__main__":
    main()
