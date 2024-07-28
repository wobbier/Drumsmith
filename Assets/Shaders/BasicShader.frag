$input v_color0, v_normal, v_texcoord0

#include "Common.sh"

SAMPLER2D(s_texDiffuse, 0);
SAMPLER2D(s_texNormal, 1);
SAMPLER2D(s_texAlpha, 2);
SAMPLER2D(s_texDiffuse0, 3);

uniform vec4 s_diffuse;
uniform vec4 s_ambient;
uniform vec4 s_sunDirection;
uniform vec4 s_sunDiffuse;
uniform vec4 s_tiling;
uniform vec4 u_skyLuminance;

void main()
{
	vec3 v3_0 = vec3( 0.000000, 0.000000, 0.000000 );
	vec2 uvs = v_texcoord0 * s_tiling.xy;
	vec4 sample_1 = texture2D( s_texDiffuse0, uvs );
	vec3 add_2 = v3_0 + sample_1.xyz;
	float f_3 = 1.000000;
	float f_4 = abs(f_3);
	vec4 finalColor = vec4(add_2.xyz, 1.f);

	finalColor.a = f_4;
	gl_FragColor = finalColor;
}
