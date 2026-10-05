# Chapter 3 profile on cloud phones (fixture)

Source: fixture

## Per-model profile

| Model | Precision | Batch | Latency ms | Peak MB | NPU share | Off-chip | Jobs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nudenet-320n | float16 | 1 | [1.8](fixture://fixture://p-nudenet-320n-float16) | [45.0](fixture://fixture://p-nudenet-320n-float16) | [1.0](fixture://fixture://p-nudenet-320n-float16) | none | [compile](fixture://fixture://c-nudenet-320n-float16), [profile](fixture://fixture://p-nudenet-320n-float16) |
| nudenet-320n | w8a16 | 1 | [1.26](fixture://fixture://p-nudenet-320n-w8a16) | [45.0](fixture://fixture://p-nudenet-320n-w8a16) | [1.0](fixture://fixture://p-nudenet-320n-w8a16) | none | [compile](fixture://fixture://c-nudenet-320n-w8a16), [profile](fixture://fixture://p-nudenet-320n-w8a16), [quantize](fixture://fixture://q-nudenet-320n-w8a16) |
| nudenet-320n | w8a8 | 1 | [0.9](fixture://fixture://p-nudenet-320n-w8a8) | [45.0](fixture://fixture://p-nudenet-320n-w8a8) | [1.0](fixture://fixture://p-nudenet-320n-w8a8) | none | [compile](fixture://fixture://c-nudenet-320n-w8a8), [profile](fixture://fixture://p-nudenet-320n-w8a8), [quantize](fixture://fixture://q-nudenet-320n-w8a8) |
| nudenet-640m | float16 | 1 | [6.5](fixture://fixture://p-nudenet-640m-float16) | [45.0](fixture://fixture://p-nudenet-640m-float16) | [1.0](fixture://fixture://p-nudenet-640m-float16) | none | [compile](fixture://fixture://c-nudenet-640m-float16), [profile](fixture://fixture://p-nudenet-640m-float16) |
| nudenet-640m | w8a16 | 1 | [4.55](fixture://fixture://p-nudenet-640m-w8a16) | [45.0](fixture://fixture://p-nudenet-640m-w8a16) | [1.0](fixture://fixture://p-nudenet-640m-w8a16) | none | [compile](fixture://fixture://c-nudenet-640m-w8a16), [profile](fixture://fixture://p-nudenet-640m-w8a16), [quantize](fixture://fixture://q-nudenet-640m-w8a16) |
| nudenet-640m | w8a8 | 1 | [3.25](fixture://fixture://p-nudenet-640m-w8a8) | [45.0](fixture://fixture://p-nudenet-640m-w8a8) | [1.0](fixture://fixture://p-nudenet-640m-w8a8) | none | [compile](fixture://fixture://c-nudenet-640m-w8a8), [profile](fixture://fixture://p-nudenet-640m-w8a8), [quantize](fixture://fixture://q-nudenet-640m-w8a8) |
| yoloe-26s-embed-top100 | float16 | 1 | [5.2](fixture://fixture://p-yoloe-26s-embed-top100-float16) | [45.0](fixture://fixture://p-yoloe-26s-embed-top100-float16) | [0.8571428571428571](fixture://fixture://p-yoloe-26s-embed-top100-float16) | post/NonZero_1 (NonZero, dynamic shape); post/NonZero_2 (NonZero, dynamic shape) | [compile](fixture://fixture://c-yoloe-26s-embed-top100-float16), [profile](fixture://fixture://p-yoloe-26s-embed-top100-float16) |
| yoloe-26s-embed-top100 | w8a16 | 1 | [3.639](fixture://fixture://p-yoloe-26s-embed-top100-w8a16) | [45.0](fixture://fixture://p-yoloe-26s-embed-top100-w8a16) | [1.0](fixture://fixture://p-yoloe-26s-embed-top100-w8a16) | none | [compile](fixture://fixture://c-yoloe-26s-embed-top100-w8a16), [profile](fixture://fixture://p-yoloe-26s-embed-top100-w8a16), [quantize](fixture://fixture://q-yoloe-26s-embed-top100-w8a16) |
| yoloe-26s-embed-top100 | w8a8 | 1 | [2.6](fixture://fixture://p-yoloe-26s-embed-top100-w8a8) | [45.0](fixture://fixture://p-yoloe-26s-embed-top100-w8a8) | [1.0](fixture://fixture://p-yoloe-26s-embed-top100-w8a8) | none | [compile](fixture://fixture://c-yoloe-26s-embed-top100-w8a8), [profile](fixture://fixture://p-yoloe-26s-embed-top100-w8a8), [quantize](fixture://fixture://q-yoloe-26s-embed-top100-w8a8) |
| siglip2-base-image-b1 | float16 | 1 | [5.6](fixture://fixture://p-siglip2-base-image-b1-float16) | [45.0](fixture://fixture://p-siglip2-base-image-b1-float16) | [1.0](fixture://fixture://p-siglip2-base-image-b1-float16) | none | [compile](fixture://fixture://c-siglip2-base-image-b1-float16), [profile](fixture://fixture://p-siglip2-base-image-b1-float16) |
| siglip2-base-image-b1 | w8a16 | 1 | [3.92](fixture://fixture://p-siglip2-base-image-b1-w8a16) | [45.0](fixture://fixture://p-siglip2-base-image-b1-w8a16) | [1.0](fixture://fixture://p-siglip2-base-image-b1-w8a16) | none | [compile](fixture://fixture://c-siglip2-base-image-b1-w8a16), [profile](fixture://fixture://p-siglip2-base-image-b1-w8a16), [quantize](fixture://fixture://q-siglip2-base-image-b1-w8a16) |
| siglip2-base-image-b16 | float16 | 16 | [89.6](fixture://fixture://p-siglip2-base-image-b16-float16) | [120.0](fixture://fixture://p-siglip2-base-image-b16-float16) | [1.0](fixture://fixture://p-siglip2-base-image-b16-float16) | none | [compile](fixture://fixture://c-siglip2-base-image-b16-float16), [profile](fixture://fixture://p-siglip2-base-image-b16-float16) |
| siglip2-base-image-b16 | w8a16 | 16 | [62.72](fixture://fixture://p-siglip2-base-image-b16-w8a16) | [120.0](fixture://fixture://p-siglip2-base-image-b16-w8a16) | [1.0](fixture://fixture://p-siglip2-base-image-b16-w8a16) | none | [compile](fixture://fixture://c-siglip2-base-image-b16-w8a16), [profile](fixture://fixture://p-siglip2-base-image-b16-w8a16), [quantize](fixture://fixture://q-siglip2-base-image-b16-w8a16) |
| siglip2-base-image-b4 | float16 | 4 | [22.4](fixture://fixture://p-siglip2-base-image-b4-float16) | [60.0](fixture://fixture://p-siglip2-base-image-b4-float16) | [1.0](fixture://fixture://p-siglip2-base-image-b4-float16) | none | [compile](fixture://fixture://c-siglip2-base-image-b4-float16), [profile](fixture://fixture://p-siglip2-base-image-b4-float16) |
| siglip2-base-image-b4 | w8a16 | 4 | [15.68](fixture://fixture://p-siglip2-base-image-b4-w8a16) | [60.0](fixture://fixture://p-siglip2-base-image-b4-w8a16) | [1.0](fixture://fixture://p-siglip2-base-image-b4-w8a16) | none | [compile](fixture://fixture://c-siglip2-base-image-b4-w8a16), [profile](fixture://fixture://p-siglip2-base-image-b4-w8a16), [quantize](fixture://fixture://q-siglip2-base-image-b4-w8a16) |
| siglip2-base-text | float16 | 1 | [3.0](fixture://fixture://p-siglip2-base-text-float16) | [45.0](fixture://fixture://p-siglip2-base-text-float16) | [1.0](fixture://fixture://p-siglip2-base-text-float16) | none | [compile](fixture://fixture://c-siglip2-base-text-float16), [profile](fixture://fixture://p-siglip2-base-text-float16) |
| siglip2-base-text | w8a16 | 1 | [2.099](fixture://fixture://p-siglip2-base-text-w8a16) | [45.0](fixture://fixture://p-siglip2-base-text-w8a16) | [1.0](fixture://fixture://p-siglip2-base-text-w8a16) | none | [compile](fixture://fixture://c-siglip2-base-text-w8a16), [profile](fixture://fixture://p-siglip2-base-text-w8a16), [quantize](fixture://fixture://q-siglip2-base-text-w8a16) |
| toxicity-seq128 | float16 | 1 | [1.2](fixture://fixture://p-toxicity-seq128-float16) | [45.0](fixture://fixture://p-toxicity-seq128-float16) | [1.0](fixture://fixture://p-toxicity-seq128-float16) | none | [compile](fixture://fixture://c-toxicity-seq128-float16), [profile](fixture://fixture://p-toxicity-seq128-float16) |
| toxicity-seq128 | w8a16 | 1 | [0.84](fixture://fixture://p-toxicity-seq128-w8a16) | [45.0](fixture://fixture://p-toxicity-seq128-w8a16) | [1.0](fixture://fixture://p-toxicity-seq128-w8a16) | none | [compile](fixture://fixture://c-toxicity-seq128-w8a16), [profile](fixture://fixture://p-toxicity-seq128-w8a16), [quantize](fixture://fixture://q-toxicity-seq128-w8a16) |
| toxicity-seq256 | float16 | 1 | [2.3](fixture://fixture://p-toxicity-seq256-float16) | [45.0](fixture://fixture://p-toxicity-seq256-float16) | [1.0](fixture://fixture://p-toxicity-seq256-float16) | none | [compile](fixture://fixture://c-toxicity-seq256-float16), [profile](fixture://fixture://p-toxicity-seq256-float16) |
| toxicity-seq256 | w8a16 | 1 | [1.609](fixture://fixture://p-toxicity-seq256-w8a16) | [45.0](fixture://fixture://p-toxicity-seq256-w8a16) | [1.0](fixture://fixture://p-toxicity-seq256-w8a16) | none | [compile](fixture://fixture://c-toxicity-seq256-w8a16), [profile](fixture://fixture://p-toxicity-seq256-w8a16), [quantize](fixture://fixture://q-toxicity-seq256-w8a16) |

## Precision

| Model | Float score | Chosen | Chosen score | Delta | Latency ms |
| --- | --- | --- | --- | --- | --- |
| nudenet-320n | [90.0](fixture://fixture://i-nudenet-320n-w8a8) | w8a8 | [88.8](fixture://fixture://i-nudenet-320n-w8a8) | [1.2](fixture://fixture://i-nudenet-320n-w8a8) | [1.6](fixture://fixture://i-nudenet-320n-w8a8) |
| nudenet-640m | [89.0](fixture://fixture://i-nudenet-640m-w8a16) | w8a16 | [88.4](fixture://fixture://i-nudenet-640m-w8a16) | [0.6](fixture://fixture://i-nudenet-640m-w8a16) | [2.42](fixture://fixture://i-nudenet-640m-w8a16) |
| yoloe-26s-embed-top100 | [88.0](fixture://fixture://i-yoloe-26s-embed-top100-w8a8) | w8a8 | [86.8](fixture://fixture://i-yoloe-26s-embed-top100-w8a8) | [1.2](fixture://fixture://i-yoloe-26s-embed-top100-w8a8) | [1.92](fixture://fixture://i-yoloe-26s-embed-top100-w8a8) |
| siglip2-base-image-b1 | [87.0](fixture://fixture://i-siglip2-base-image-b1-w8a16) | w8a16 | [86.4](fixture://fixture://i-siglip2-base-image-b1-w8a16) | [0.6](fixture://fixture://i-siglip2-base-image-b1-w8a16) | [5.85](fixture://fixture://i-siglip2-base-image-b1-w8a16) |
| siglip2-base-image-b4 | [86.0](fixture://fixture://i-siglip2-base-image-b4-w8a16) | w8a16 | [85.4](fixture://fixture://i-siglip2-base-image-b4-w8a16) | [0.6](fixture://fixture://i-siglip2-base-image-b4-w8a16) | [6.3](fixture://fixture://i-siglip2-base-image-b4-w8a16) |
| siglip2-base-image-b16 | [85.0](fixture://fixture://i-siglip2-base-image-b16-w8a16) | w8a16 | [84.4](fixture://fixture://i-siglip2-base-image-b16-w8a16) | [0.6](fixture://fixture://i-siglip2-base-image-b16-w8a16) | [6.75](fixture://fixture://i-siglip2-base-image-b16-w8a16) |
| toxicity-seq128 | [84.0](fixture://fixture://i-toxicity-seq128-w8a16) | w8a16 | [83.4](fixture://fixture://i-toxicity-seq128-w8a16) | [0.6](fixture://fixture://i-toxicity-seq128-w8a16) | [7.2](fixture://fixture://i-toxicity-seq128-w8a16) |
| toxicity-seq256 | [83.0](fixture://fixture://i-toxicity-seq256-w8a16) | w8a16 | [82.4](fixture://fixture://i-toxicity-seq256-w8a16) | [0.6](fixture://fixture://i-toxicity-seq256-w8a16) | [7.65](fixture://fixture://i-toxicity-seq256-w8a16) |

## Budget (Balanced)

| Step | ms | Job |
| --- | --- | --- |
| preprocessing (estimated) | 3.0 | estimated |
| nudenet-320n | [2.1](fixture://fpnudenet-320n) | fpnudenet-320n |
| yoloe-26s | [4.8](fixture://fpyoloe-26s-embed-top100) | fpyoloe-26s-embed-top100 |
| siglip2 image b4 | [14.5](fixture://fpsiglip2-base-image-b4) | fpsiglip2-base-image-b4 |
| toxicity-seq128 | [3.2](fixture://fptoxicity-seq128) | fptoxicity-seq128 |
| logic (estimated) | 1.0 | estimated |
| Total (limit 45.0 ms, pass=True) | 28.6 | sum |

## Modes

| Mode | Total ms | Pass |
| --- | --- | --- |
| Light | 20.1 | True |
| Balanced | 28.6 | True |
| Strict | 67.2 | False |

Note: YOLOE only exists in size 26s, so Light and Strict reuse it.
