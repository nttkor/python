cbuffer Transform : register(b0)
{
    matrix mvp;
};

struct VSInput {
    float3 position : POSITION;
};

struct VSOutput {
    float4 position : SV_POSITION;
};

VSOutput main(VSInput input) {
    VSOutput output;
    output.position = mul(mvp, float4(input.position, 1.0));
    return output;
}