import time
import pickle

import torch
import torch.distributed as dist
import habana_frameworks.torch.core as htcore

from fastfold.config import model_config
from fastfold.model.hub import AlphaFold

from fastfold.habana.inject_habana import inject_habana
from fastfold.habana.distributed import init_dist
from fastfold.habana.fastnn.ops import set_chunk_size


def main():
    init_dist()

    batch = pickle.load(open('./test_batch_512.pkl', 'rb'))

    model_name = "model_1"
    device = torch.device("hpu")

    config = model_config(model_name)
    config.globals.inplace = False
    config.globals.chunk_size = 512
    config.globals.hmp_enable = True
    model = AlphaFold(config)
    model = inject_habana(model)
    model = model.eval()
    model = model.to(device=device)

    set_chunk_size(model.globals.chunk_size + 1)

    if config.globals.hmp_enable:
        from habana_frameworks.torch.hpex import hmp
        hmp.convert(opt_level='O1', bf16_file_path='./habana/ops_bf16.txt', fp32_file_path='./habana/ops_fp32.txt', isVerbose=False)
        print("========= AMP ENABLED!!")

    with torch.no_grad():
        batch = {k: torch.as_tensor(v).to(device=device) for k, v in batch.items()}

        for _ in range(5):
            t = time.perf_counter()
            out = model(batch)
            htcore.mark_step()
            print(f"Inference time: {time.perf_counter() - t}")


if __name__ == '__main__':
    main()
