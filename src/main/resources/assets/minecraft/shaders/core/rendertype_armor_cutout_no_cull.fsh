#version 150

uniform sampler2D Sampler0;

uniform vec4 ColorModulator;
uniform float FogStart;
uniform float FogEnd;
uniform vec4 FogColor;

in float vertexDistance;
in vec3 viewPos;
in vec4 vertexColor;
in vec2 texCoord0;

out vec4 fragColor;

const float NEAR_DIST = 0.35;
const float FAR_DIST = 1.5;

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

void main() {
    float camDist = length(viewPos);
    if (FogStart < 1.0e6 && camDist < FAR_DIST) {
        float visibility = smoothstep(NEAR_DIST, FAR_DIST, camDist);
        ivec2 cell = ivec2(mod(gl_FragCoord.xy, 4.0));
        float threshold = (BAYER4[cell.y * 4 + cell.x] + 0.5) / 16.0;
        if (visibility <= threshold) {
            discard;
        }
    }

    vec4 color = texture(Sampler0, texCoord0) * vertexColor * ColorModulator;
    if (color.a < 0.1) {
        discard;
    }
    fragColor = linear_fog(color, vertexDistance, FogStart, FogEnd, FogColor);
}
