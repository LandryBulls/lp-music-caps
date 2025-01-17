import os
import numpy as np
import torch
from lpmc.music_captioning.model.bart import BartCaptionModel
from lpmc.utils.eval_utils import load_pretrained
from lpmc.utils.audio_utils import load_audio, STR_CH_FIRST
from omegaconf import OmegaConf

def get_audio(audio_path, duration=10, target_sr=16000):
    n_samples = int(duration * target_sr)
    audio, sr = load_audio(
        path= audio_path,
        ch_format= STR_CH_FIRST,
        sample_rate= target_sr,
        downmix_to_mono= True,
    )
    if len(audio.shape) == 2:
        audio = audio.mean(0, False)  # to mono
    input_size = int(n_samples)
    if audio.shape[-1] < input_size:  # pad sequence
        pad = np.zeros(input_size)
        pad[: audio.shape[-1]] = audio
        audio = pad
    ceil = int(audio.shape[-1] // n_samples)
    audio = torch.from_numpy(np.stack(np.split(audio[:ceil * n_samples], ceil)).astype('float32'))
    return audio

def captioning(audio_path, framework="transfer", caption_type="lp_music_caps", max_length=128, num_beams=5, model_type="last"):
    save_dir = f"exp/{framework}/{caption_type}/"
    config = OmegaConf.load(os.path.join(save_dir, "hparams.yaml"))
    model = BartCaptionModel(max_length = config.max_length)
    args = type('', (), {})()
    args.model_type = model_type
    args.multiprocessing_distributed = False
    model, save_epoch = load_pretrained(args, save_dir, model, mdp=config.multiprocessing_distributed)
    model.eval()
    
    audio_tensor = get_audio(audio_path = audio_path)

    with torch.no_grad():
        output = model.generate(
            samples=audio_tensor,
            num_beams=num_beams,
        )
    inference = {}
    number_of_chunks = range(audio_tensor.shape[0])
    for chunk, text in zip(number_of_chunks, output):
        time = f"{chunk * 10}:00-{(chunk + 1) * 10}:00"
        item = {"text":text,"time":time}
        inference[chunk] = item
    return inference
