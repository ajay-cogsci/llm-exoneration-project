### quality

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B - A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 59.1 | 58.2 | -0.9 [-1.5, -0.2] (level shift) | |
| Gemma 4 31B IT | cleared | +1.0 [+0.4, +1.6] | +0.6 [+0.0, +1.2] | -0.4 [-1.2, +0.4] | -0.1 |
| Gemma 4 31B IT | pending | -2.6 [-3.3, -2.0] | -2.7 [-3.4, -2.0] | -0.1 [-0.9, +0.7] | +0.0 |
| Gemma 4 31B IT | responsible | -8.3 [-9.2, -7.5] | -8.6 [-9.6, -7.6] | -0.2 [-1.2, +0.7] | +0.0 |
| Qwen3-32B | clean (mean score) | 68.4 | 68.8 | +0.3 [-0.4, +1.1] (level shift) | |
| Qwen3-32B | cleared | +0.6 [-0.2, +1.4] | -0.0 [-0.7, +0.7] | -0.6 [-1.6, +0.4] | +0.9 |
| Qwen3-32B | pending | -4.9 [-5.8, -3.9] | -5.2 [-6.1, -4.4] | -0.4 [-1.5, +0.7] | +1.6 |
| Qwen3-32B | responsible | -9.5 [-10.6, -8.4] | -10.2 [-11.3, -9.1] | -0.7 [-2.2, +0.8] | +1.4 |
| GPT-5.4 mini | clean (mean score) | 64.3 | 64.7 | +0.4 [-0.3, +1.0] (level shift) | |
| GPT-5.4 mini | cleared | -1.0 [-1.7, -0.3] | -0.9 [-1.5, -0.2] | +0.1 [-0.8, +1.1] | -0.1 |
| GPT-5.4 mini | pending | -7.6 [-8.7, -6.6] | -7.4 [-8.2, -6.6] | +0.2 [-1.0, +1.4] | +0.5 |
| GPT-5.4 mini | responsible | -15.1 [-16.3, -13.9] | -15.2 [-16.3, -14.1] | -0.1 [-1.2, +1.0] | -0.3 |

### advance

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B - A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 52.6 | 51.7 | -0.8 [-1.5, -0.2] (level shift) | |
| Gemma 4 31B IT | cleared | +1.6 [+0.7, +2.5] | +1.4 [+0.7, +2.1] | -0.3 [-1.4, +0.9] | -0.4 |
| Gemma 4 31B IT | pending | -3.0 [-3.7, -2.2] | -3.4 [-4.3, -2.5] | -0.4 [-1.4, +0.5] | -0.2 |
| Gemma 4 31B IT | responsible | -13.9 [-15.7, -12.1] | -14.1 [-16.0, -12.1] | -0.1 [-1.4, +1.1] | -0.7 |
| Qwen3-32B | clean (mean score) | 64.9 | 65.0 | +0.2 [-0.9, +1.2] (level shift) | |
| Qwen3-32B | cleared | -0.7 [-1.8, +0.5] | -0.6 [-1.6, +0.4] | +0.1 [-1.5, +1.7] | -1.5 |
| Qwen3-32B | pending | -9.0 [-10.2, -7.8] | -8.6 [-9.7, -7.4] | +0.4 [-1.1, +1.9] | -0.9 |
| Qwen3-32B | responsible | -16.3 [-17.9, -14.7] | -17.4 [-18.9, -15.9] | -1.1 [-2.9, +0.7] | +0.1 |
| GPT-5.4 mini | clean (mean score) | 62.4 | 62.7 | +0.3 [-0.8, +1.4] (level shift) | |
| GPT-5.4 mini | cleared | +1.4 [+0.3, +2.5] | +1.3 [+0.3, +2.3] | -0.1 [-1.6, +1.3] | -0.3 |
| GPT-5.4 mini | pending | -11.6 [-13.0, -10.2] | -11.0 [-12.5, -9.5] | +0.6 [-0.9, +2.1] | -0.6 |
| GPT-5.4 mini | responsible | -29.9 [-32.5, -27.4] | -29.2 [-31.2, -27.2] | +0.8 [-1.0, +2.5] | -1.4 |

### decide

| Model | Condition | Gap vs clean, A (original) | Gap vs clean, B (removed) | Removal effect B - A | Re-run noise (A vs main) |
|---|---|---|---|---|---|
| Gemma 4 31B IT | clean (mean score) | 49.6 | 48.9 | -0.8 [-1.6, +0.0] (level shift) | |
| Gemma 4 31B IT | cleared | +0.8 [-0.1, +1.7] | +0.2 [-0.5, +0.9] | -0.6 [-1.6, +0.4] | +0.2 |
| Gemma 4 31B IT | pending | -5.2 [-6.3, -4.2] | -4.9 [-5.8, -3.9] | +0.4 [-0.7, +1.5] | -1.1 |
| Gemma 4 31B IT | responsible | -16.4 [-18.4, -14.4] | -15.6 [-17.5, -13.7] | +0.8 [-0.4, +2.1] | -0.3 |
| Qwen3-32B | clean (mean score) | 63.6 | 63.4 | -0.2 [-1.3, +0.9] (level shift) | |
| Qwen3-32B | cleared | +0.8 [-0.3, +1.9] | +0.8 [-0.2, +1.8] | +0.0 [-1.4, +1.4] | -0.0 |
| Qwen3-32B | pending | -7.0 [-8.1, -5.9] | -7.1 [-8.2, -5.9] | -0.0 [-1.5, +1.5] | +1.1 |
| Qwen3-32B | responsible | -14.0 [-15.4, -12.5] | -14.8 [-16.3, -13.3] | -0.8 [-2.3, +0.7] | +0.5 |
| GPT-5.4 mini | clean (mean score) | 56.5 | 57.7 | +1.3 [+0.1, +2.5] (level shift) | |
| GPT-5.4 mini | cleared | -0.1 [-1.3, +1.1] | -0.6 [-1.8, +0.5] | -0.6 [-2.1, +1.0] | +0.8 |
| GPT-5.4 mini | pending | -14.2 [-16.1, -12.3] | -13.5 [-15.2, -11.8] | +0.7 [-1.2, +2.6] | -0.4 |
| GPT-5.4 mini | responsible | -29.2 [-32.0, -26.5] | -29.3 [-31.9, -26.6] | -0.0 [-1.9, +1.9] | -0.2 |

### Noise level per model (absolute difference in condition-vs-clean gaps, arm A vs the main run, 9 gaps per model)

| Model | Median | Mean | Max |
|---|---|---|---|
| Gemma 4 31B IT | 0.18 | 0.34 | 1.15 |
| Qwen3-32B | 0.94 | 0.89 | 1.59 |
| GPT-5.4 mini | 0.41 | 0.53 | 1.45 |
