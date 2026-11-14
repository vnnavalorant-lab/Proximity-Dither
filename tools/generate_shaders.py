#!/usr/bin/env python3
"""Regera os shaders (json/vsh/fsh) do mod.

    python3 tools/generate_shaders.py
    python3 tools/generate_shaders.py --near 0.5 --far 2.5

near: abaixo dessa distância (em blocos) a entidade some por completo
far:  a partir daqui ela aparece inteira
"""
import argparse
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src/main/resources/assets/minecraft/shaders/core"

# nome do programa -> (descarta alpha baixo, usa o formato de vértice da armadura)
PROGRAMS = {
    "rendertype_entity_cutout":         (True,  False),
    "rendertype_entity_cutout_no_cull": (True,  False),
    "rendertype_entity_solid":          (False, False),
    "rendertype_entity_translucent":    (True,  False),
    "rendertype_armor_cutout_no_cull":  (True,  True),
}

# ---------------------------------------------------------------- vertex

VSH_HEAD = """#version 150

#define MINECRAFT_LIGHT_POWER   (0.6)
#define MINECRAFT_AMBIENT_LIGHT (0.4)

in vec3 Position;
in vec4 Color;
in vec2 UV0;
in ivec2 UV1;
in ivec2 UV2;
in vec3 Normal;
"""

VSH_FUNCS = """
vec4 minecraft_mix_light(vec3 lightDir0, vec3 lightDir1, vec3 normal, vec4 color) {
    lightDir0 = normalize(lightDir0);
    lightDir1 = normalize(lightDir1);
    float light0 = max(0.0, dot(lightDir0, normal));
    float light1 = max(0.0, dot(lightDir1, normal));
    float lightAccum = min(1.0, (light0 + light1) * MINECRAFT_LIGHT_POWER + MINECRAFT_AMBIENT_LIGHT);
    return vec4(color.rgb * lightAccum, color.a);
}

float fog_distance(mat4 modelViewMat, vec3 pos, int shape) {
    if (shape == 0) {
        return length((modelViewMat * vec4(pos, 1.0)).xyz);
    }
    float distXZ = length((modelViewMat * vec4(pos.x, 0.0, pos.z, 1.0)).xyz);
    float distY = length((modelViewMat * vec4(0.0, pos.y, 0.0, 1.0)).xyz);
    return max(distXZ, distY);
}
"""

VSH_ENTITY = VSH_HEAD + """
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
""" + VSH_FUNCS + """
void main() {
    vec4 viewPosition = ModelViewMat * vec4(Position, 1.0);
    gl_Position = ProjMat * viewPosition;

    vertexDistance = fog_distance(ModelViewMat, IViewRotMat * Position, FogShape);
    viewPos = viewPosition.xyz;
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);
    lightMapColor = texelFetch(Sampler2, UV2 / 16, 0);
    overlayColor = texelFetch(Sampler1, UV1, 0);
    texCoord0 = UV0;
}
"""

# armadura: sem IViewRotMat nem overlay, e o lightmap já entra no vertexColor
VSH_ARMOR = VSH_HEAD + """
uniform sampler2D Sampler2;

uniform mat4 ModelViewMat;
uniform mat4 ProjMat;
uniform int FogShape;

uniform vec3 Light0_Direction;
uniform vec3 Light1_Direction;

out float vertexDistance;
out vec3 viewPos;
out vec4 vertexColor;
out vec2 texCoord0;
""" + VSH_FUNCS + """
void main() {
    vec4 viewPosition = ModelViewMat * vec4(Position, 1.0);
    gl_Position = ProjMat * viewPosition;

    vertexDistance = fog_distance(ModelViewMat, Position, FogShape);
    viewPos = viewPosition.xyz;
    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color) * texelFetch(Sampler2, UV2 / 16, 0);
    texCoord0 = UV0;
}
"""

# -------------------------------------------------------------- fragment

FSH_HEAD = """#version 150

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec3 viewPos;
in vec4 vertexColor;
"""

FSH_CONSTS = """
out vec4 fragColor;

const float NEAR_DIST = @NEAR@;
const float FAR_DIST = @FAR@;

const float BAYER4[16] = float[16](
     0.0,  8.0,  2.0, 10.0,
    12.0,  4.0, 14.0,  6.0,
     3.0, 11.0,  1.0,  9.0,
    15.0,  7.0, 13.0,  5.0
);

vec4 linear_fog(vec4 inColor, float dist, float fogStart, float fogEnd, vec4 fogColor) {
    if (dist <= fogStart) {
        return inColor;
    }
    float fogValue = dist < fogEnd ? smoothstep(fogStart, fogEnd, dist) : 1.0;
    return vec4(mix(inColor.rgb, fogColor.rgb, fogValue * fogColor.a), inColor.a);
}
"""

DITHER = """    float camDist = length(viewPos);
    if (FogStart < 1.0e6 && camDist < FAR_DIST) {
        float visibility = smoothstep(NEAR_DIST, FAR_DIST, camDist);
        ivec2 cell = ivec2(mod(gl_FragCoord.xy, 4.0));
        float threshold = (BAYER4[cell.y * 4 + cell.x] + 0.5) / 16.0;
        if (visibility <= threshold) {
            discard;
        }
    }
"""

ALPHA = """    if (color.a < 0.1) {
        discard;
    }
"""

FSH_ENTITY = FSH_HEAD + """in vec4 lightMapColor;
in vec4 overlayColor;
in vec2 texCoord0;
""" + FSH_CONSTS + """
void main() {
    // hand and GUI items come with a huge FogStart, skip them
""" + DITHER + """
    vec4 color = texture(Sampler0, texCoord0);
@ALPHA@    color *= vertexColor * ColorModulator;
    color.rgb = mix(overlayColor.rgb, color.rgb, overlayColor.a);
    color *= lightMapColor;
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
"""

FSH_ARMOR = FSH_HEAD + """in vec2 texCoord0;
""" + FSH_CONSTS + """
void main() {
""" + DITHER + """
    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
@ALPHA@    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
"""

# ------------------------------------------------------------------ json

def program_json(name, armor):
    mat4 = [1.0 if i % 5 == 0 else 0.0 for i in range(16)]
    mat3 = [1.0 if i % 4 == 0 else 0.0 for i in range(9)]

    uniforms = [
        {"name": "ModelViewMat", "type": "matrix4x4", "count": 16, "values": mat4},
        {"name": "ProjMat", "type": "matrix4x4", "count": 16, "values": mat4},
    ]
    if not armor:
        uniforms.append({"name": "IViewRotMat", "type": "matrix3x3", "count": 9, "values": mat3})
    uniforms += [
        {"name": "ColorModulator", "type": "float", "count": 4, "values": [1.0, 1.0, 1.0, 1.0]},
        {"name": "Light0_Direction", "type": "float", "count": 3, "values": [0.0, 0.0, 0.0]},
        {"name": "Light1_Direction", "type": "float", "count": 3, "values": [0.0, 0.0, 0.0]},
        {"name": "FogStart", "type": "float", "count": 1, "values": [0.0]},
        {"name": "FogEnd", "type": "float", "count": 1, "values": [1.0]},
        {"name": "FogColor", "type": "float", "count": 4, "values": [0.0, 0.0, 0.0, 0.0]},
        {"name": "FogShape", "type": "int", "count": 1, "values": [0]},
    ]

    samplers = ["Sampler0", "Sampler2"] if armor else ["Sampler0", "Sampler1", "Sampler2"]
    return {
        "blend": {"func": "add", "srcrgb": "srcalpha", "dstrgb": "1-srcalpha"},
        "vertex": name,
        "fragment": name,
        # sem isso o jogo não liga Color/UV1/UV2/Normal e tudo sai preto
        "attributes": ["Position", "Color", "UV0", "UV1", "UV2", "Normal"],
        "samplers": [{"name": s} for s in samplers],
        "uniforms": uniforms,
    }


def main():
    ap = argparse.ArgumentParser(description="Gera os shaders do mod.")
    ap.add_argument("--near", type=float, default=0.35, help="distância onde some por completo (padrão 0.35)")
    ap.add_argument("--far", type=float, default=1.5, help="distância onde fica totalmente visível (padrão 1.5)")
    args = ap.parse_args()
    if not 0.0 <= args.near < args.far:
        ap.error("precisa de 0 <= near < far")

    OUT.mkdir(parents=True, exist_ok=True)
    for name, (alpha_test, armor) in PROGRAMS.items():
        fsh = (FSH_ARMOR if armor else FSH_ENTITY)
        fsh = (fsh.replace("@NEAR@", repr(args.near))
                  .replace("@FAR@", repr(args.far))
                  .replace("@ALPHA@", ALPHA if alpha_test else ""))
        (OUT / f"{name}.vsh").write_text(VSH_ARMOR if armor else VSH_ENTITY)
        (OUT / f"{name}.fsh").write_text(fsh)
        (OUT / f"{name}.json").write_text(json.dumps(program_json(name, armor), indent=4) + "\n")

    print(f"{len(PROGRAMS)} programas em {OUT} (near={args.near}, far={args.far})")


if __name__ == "__main__":
    main()
