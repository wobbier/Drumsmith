$input v_texcoord0

// Generated from Assets/ShaderGraphs/Venue/Camcorder.shadergraph by the shader graph compiler: edit the graph, not this file.
// A full-screen pass (with the engine's Post/Fullscreen.vert) on the HDR scene before tonemapping,
// or on the display image after it (the graph's Injection setting).
#define SG_TARGET_POST 1

#include "Common.sh"
#include "ShaderGraph/SGLib.sh"

SAMPLER2D(s_sgSceneColor, 6);
SAMPLER2D(s_sgSceneDepth, 7);
uniform vec4 u_sgPostProjection;   // x P[2][2], y P[3][2], z 1 = orthographic, w 1 = depth range -1..1
uniform vec4 u_sgPostProjection2;  // x P[0][0], y P[1][1], z far distance (sky)
uniform mat4 u_sgPostInvView;      // the camera's view -> world (full-screen views are orthographic)

vec3 sgSceneColor(vec2 _uv)
{
	return texture2DLod(s_sgSceneColor, _uv, 0.0).rgb;
}

// Linear view depth (distance along the view) of the opaque scene under a screen UV.
float sgSceneDepth(vec2 _uv)
{
	float raw = texture2DLod(s_sgSceneDepth, _uv, 0.0).r;
	if (raw >= 0.99999)
	{
		return u_sgPostProjection2.z;
	}
	float ndc = u_sgPostProjection.w > 0.5 ? raw * 2.0 - 1.0 : raw;
	if (u_sgPostProjection.z > 0.5)
	{
		return (ndc - u_sgPostProjection.y) / u_sgPostProjection.x;
	}
	return u_sgPostProjection.y / (ndc - u_sgPostProjection.x);
}

// The view-space position of the scene under a screen UV (top-left origin).
vec3 sgViewPosition(vec2 _uv)
{
	vec2 ndc = vec2(_uv.x * 2.0 - 1.0, 1.0 - _uv.y * 2.0);
	vec2 scale = vec2(1.0 / u_sgPostProjection2.x, 1.0 / u_sgPostProjection2.y);
	float viewZ = sgSceneDepth(_uv);
	return u_sgPostProjection.z > 0.5 ? vec3(ndc * scale, viewZ) : vec3(ndc * scale * viewZ, viewZ);
}

// The scene's view-space normal, from one-pixel depth taps on the flatter side of each axis.
vec3 sgViewNormal(vec2 _uv)
{
	vec3 center = sgViewPosition(_uv);
	vec2 dx = vec2(u_viewTexel.x, 0.0);
	vec2 dy = vec2(0.0, u_viewTexel.y);
	vec3 left = sgViewPosition(_uv - dx);
	vec3 right = sgViewPosition(_uv + dx);
	vec3 up = sgViewPosition(_uv - dy);
	vec3 down = sgViewPosition(_uv + dy);
	vec3 stepX = abs(right.z - center.z) < abs(center.z - left.z) ? right - center : center - left;
	vec3 stepY = abs(down.z - center.z) < abs(center.z - up.z) ? down - center : center - up;
	vec3 normal = sgSafeNormalize(cross(stepX, stepY));
	return dot(normal, center) > 0.0 ? -normal : normal;
}

uniform vec4 u_sgParams[16];
// u_sgParams[0]: Bleed (Float)
// u_sgParams[1]: Sharpen (Float)
// u_sgParams[2]: Smear (Float)
// u_sgParams[3]: Block (Float)
// u_sgParams[4]: Noise (Float)
// u_sgParams[5]: Break (Float)
// u_sgParams[6]: Seed (Float)
// u_sgParams[7]: Stamp (Float)
// u_sgParams[8]: StampDate (Float)
// u_sgParams[9]: StampYear (Float)
// u_sgParams[10]: StampClock (Float)

void sgCustom_Camcorder_63777(vec2 UV, float Bleed, float Sharpen, float Smear, float Block, float Noise, float Break, float Seed, float Stamp, float StampDate, float StampYear, float StampClock, out vec3 Color)
{
// A home video's picture: Drumsmith's found-footage venues (Docs/Venue-and-Band.md, "Found footage").
vec2 texel = u_viewTexel.xy;
if (Break > 0.99)
{
    // The REC break: black while the tape stops and starts.
    Color = vec3_splat(0.0);
    return;
}
vec2 uv = UV;
float row = floor(uv.y / texel.y);
// The tape getting up to speed: rows slip sideways and the band at the bottom (the head switch) tears.
float slip = fract(sin(row * 12.9898 + Seed * 78.233) * 43758.5453) - 0.5;
float band = step(1.0 - 0.025 - 0.06 * Break, uv.y) * step(0.001, Break);
uv.x += Break * (slip * 0.012 + band * (0.03 + 0.05 * fract(sin(row * 3.7 + Seed) * 951.3)));
// A phone's resolution: the picture in blocks, its colour in blocks twice the size.
vec2 lumaUV = uv;
vec2 chromaUV = uv;
if (Block > 0.5)
{
    vec2 cell = texel * Block;
    lumaUV = (floor(uv / cell) + vec2_splat(0.5)) * cell;
    chromaUV = (floor(uv / (cell * 2.0)) + vec2_splat(0.5)) * cell * 2.0;
}
vec3 weights = vec3(0.299, 0.587, 0.114);
float luma = dot(sgSceneColor(lumaUV), weights);
// The camera's sharpening along the scan line: a halo either side of every edge.
vec2 side = vec2(texel.x * max(Block, 1.0) * 1.5, 0.0);
float around = 0.5 * (dot(sgSceneColor(lumaUV - side), weights) + dot(sgSceneColor(lumaUV + side), weights));
luma += Sharpen * (luma - around);
// The colour trails to the right: chroma averaged over the pixels to the left.
vec2 chroma = vec2_splat(0.0);
for (int i = 0; i < 6; i++)
{
    vec3 tap = sgSceneColor(chromaUV - vec2(texel.x * Bleed * float(i) / 5.0, 0.0));
    float y = dot(tap, weights);
    chroma += vec2(tap.z - y, tap.x - y);
}
chroma = chroma / 6.0;
// Blown highlights streak along the line instead of glowing.
float streak = 0.0;
for (int k = 1; k <= 8; k++)
{
    float w = 1.0 - float(k) / 9.0;
    vec2 o = vec2(texel.x * 3.0 * float(k), 0.0);
    streak += w * (max(dot(sgSceneColor(uv - o), weights) - 0.82, 0.0) + max(dot(sgSceneColor(uv + o), weights) - 0.82, 0.0));
}
streak = streak * Smear * 0.6;
float r = luma + chroma.y;
float b = luma + chroma.x;
float g = (luma - 0.299 * r - 0.114 * b) / 0.587;
vec3 color = vec3(r, g, b) + vec3(1.0, 0.93, 0.8) * streak;
// Coloured noise, worst in the dark.
vec2 pixel = floor(uv / texel);
vec3 noise = vec3(fract(sin(dot(pixel + vec2_splat(Seed), vec2(12.9898, 78.233))) * 43758.5453),
    fract(sin(dot(pixel + vec2_splat(Seed * 1.7), vec2(39.346, 11.135))) * 43758.5453),
    fract(sin(dot(pixel + vec2_splat(Seed * 2.3), vec2(73.156, 52.235))) * 43758.5453)) - vec3_splat(0.5);
float dark = 1.0 - clamp(luma * 1.6, 0.0, 1.0);
color += noise * (Noise * (0.25 + dark * dark));
// Compression: each macroblock sits a touch off its neighbours.
if (Block > 0.5)
{
    vec2 blockId = floor(uv / (texel * Block * 8.0));
    color += vec3_splat((fract(sin(dot(blockId + vec2_splat(Seed * 0.37), vec2(27.17, 91.31))) * 43758.5453) - 0.5) * 0.035);
}
// The camcorder's date and time, burned into the picture bottom right (Stamp on): two lines of
// a chunky 3x5 font with a dark edge, "JUL  4 2004" over "11:47:32 PM".
if (Stamp > 0.5)
{
    float month = floor(StampDate / 100.0);
    float day = mod(StampDate, 100.0);
    float monthCodes = 0.0;
    if (month < 1.5) monthCodes = 19862.0;
    else if (month < 2.5) monthCodes = 17933.0;
    else if (month < 3.5) monthCodes = 21913.0;
    else if (month < 4.5) monthCodes = 13081.0;
    else if (month < 5.5) monthCodes = 21918.0;
    else if (month < 6.5) monthCodes = 20374.0;
    else if (month < 7.5) monthCodes = 20372.0;
    else if (month < 8.5) monthCodes = 13202.0;
    else if (month < 9.5) monthCodes = 27160.0;
    else if (month < 10.5) monthCodes = 24027.0;
    else if (month < 11.5) monthCodes = 23293.0;
    else if (month < 12.5) monthCodes = 15886.0;
    float clock = mod(StampClock, 86400.0);
    float hours = floor(clock / 3600.0);
    float minutes = floor(mod(clock, 3600.0) / 60.0);
    float seconds = floor(mod(clock, 60.0));
    float hours12 = mod(hours + 11.0, 12.0) + 1.0;
    vec2 size = vec2(1.0, 1.0) / texel;
    float px = max(floor(size.y / 160.0), 1.0);
    vec2 cell = vec2(4.0, 7.0) * px;
    vec2 origin = vec2(size.x * 0.93 - cell.x * 11.0, size.y * 0.92 - cell.y * 2.0);
    float lit = 0.0;
    float edge = 0.0;
    for (int k = 0; k < 2; k++)
    {
        vec2 local = floor(uv / texel) - origin - (k == 0 ? vec2(px, px) : vec2_splat(0.0));
        float textLine = floor(local.y / cell.y);
        float column = floor(local.x / cell.x);
        float gx = floor(mod(local.x, cell.x) / px);
        float gy = floor(mod(local.y, cell.y) / px);
        if (local.x < 0.0 || local.y < 0.0 || textLine > 1.5 || column > 10.5 || gx > 2.5 || gy > 4.5)
        {
            continue;
        }
        float code = 11.0;
        if (textLine < 0.5)
        {
            if (column < 2.5) code = column < 0.5 ? floor(monthCodes / 1024.0) : column < 1.5 ? mod(floor(monthCodes / 32.0), 32.0) : mod(monthCodes, 32.0);
            else if (column > 3.5 && column < 4.5) code = day < 9.5 ? 11.0 : floor(day / 10.0);
            else if (column > 4.5 && column < 5.5) code = mod(day, 10.0);
            else if (column > 6.5) code = mod(floor(StampYear / pow(10.0, 10.0 - column)), 10.0);
        }
        else
        {
            if (column < 0.5) code = hours12 < 9.5 ? 11.0 : 1.0;
            else if (column < 1.5) code = mod(hours12, 10.0);
            else if (column < 2.5 || (column > 4.5 && column < 5.5)) code = 10.0;
            else if (column < 3.5) code = floor(minutes / 10.0);
            else if (column < 4.5) code = mod(minutes, 10.0);
            else if (column < 6.5) code = floor(seconds / 10.0);
            else if (column < 7.5) code = mod(seconds, 10.0);
            else if (column > 8.5 && column < 9.5) code = hours < 11.5 ? 12.0 : 24.0;
            else if (column > 9.5) code = 21.0;
        }
        float glyph = 0.0;
        if (code < 0.5) glyph = 31599.0;
        else if (code < 1.5) glyph = 11415.0;
        else if (code < 2.5) glyph = 29671.0;
        else if (code < 3.5) glyph = 29391.0;
        else if (code < 4.5) glyph = 23497.0;
        else if (code < 5.5) glyph = 31183.0;
        else if (code < 6.5) glyph = 31215.0;
        else if (code < 7.5) glyph = 29330.0;
        else if (code < 8.5) glyph = 31727.0;
        else if (code < 9.5) glyph = 31695.0;
        else if (code < 10.5) glyph = 1040.0;
        else if (code < 11.5) glyph = 0.0;
        else if (code < 12.5) glyph = 11245.0;
        else if (code < 13.5) glyph = 27566.0;
        else if (code < 14.5) glyph = 14627.0;
        else if (code < 15.5) glyph = 27502.0;
        else if (code < 16.5) glyph = 31143.0;
        else if (code < 17.5) glyph = 31140.0;
        else if (code < 18.5) glyph = 14699.0;
        else if (code < 19.5) glyph = 4714.0;
        else if (code < 20.5) glyph = 18727.0;
        else if (code < 21.5) glyph = 24557.0;
        else if (code < 22.5) glyph = 27501.0;
        else if (code < 23.5) glyph = 11114.0;
        else if (code < 24.5) glyph = 27556.0;
        else if (code < 25.5) glyph = 27565.0;
        else if (code < 26.5) glyph = 14478.0;
        else if (code < 27.5) glyph = 29842.0;
        else if (code < 28.5) glyph = 23407.0;
        else if (code < 29.5) glyph = 23402.0;
        else if (code < 30.5) glyph = 23186.0;
        float on = mod(floor(glyph / exp2((4.0 - gy) * 3.0 + (2.0 - gx))), 2.0);
        if (k == 0) edge = on; else lit = on;
    }
    color = mix(color, vec3_splat(0.05), edge * (1.0 - lit) * 0.8);
    color = mix(color, vec3(0.95, 0.95, 0.9), lit);
}
// The tear's rainbow.
color = mix(color, vec3(0.9, 0.25, 0.8) * fract(row * 0.37 + Seed * 0.11), band * Break * 0.5);
Color = clamp(color, vec3_splat(0.0), vec3_splat(1.0));
}


void main()
{
	vec4 sg_fragCoord = gl_FragCoord;
	vec2 sg_UV0 = v_texcoord0;

	// Camcorder #20
	vec3 n20_Color;
	sgCustom_Camcorder_63777(sg_UV0, u_sgParams[0].x, u_sgParams[1].x, u_sgParams[2].x, u_sgParams[3].x, u_sgParams[4].x, u_sgParams[5].x, u_sgParams[6].x, u_sgParams[7].x, u_sgParams[8].x, u_sgParams[9].x, u_sgParams[10].x, n20_Color);
	// Outputs
	vec3 sgOut_Color = n20_Color;

	gl_FragColor = vec4(sgOut_Color, 1.0);
}
