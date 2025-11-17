"""
CLI for Text-to-Audio Converter using Hugging Face TTS.
"""

import typer
import os
import pathlib
import re
from bs4 import BeautifulSoup
import torch
from transformers import pipeline
import numpy as np
import soundfile as sf
from pydub import AudioSegment


def convert(
    input_file: str,
    output: str = typer.Option(None, "-o", "--output"),
    model: str = "suno/bark-small",
    device: str = "cpu",
    chunk_size: int = 1000,
    sample_rate: int = typer.Option(None),
):
    """
    Convert text file to audio using Hugging Face TTS.
    """
    # Determine output file
    if not output:
        stem = pathlib.Path(input_file).stem
        output = f"{stem}.wav"

    # Read and clean text
    file_path = pathlib.Path(input_file)
    if not file_path.exists():
        typer.echo(f"Error: Input file '{input_file}' does not exist.")
        raise typer.Exit(1)

    suffix = file_path.suffix.lower()
    if suffix not in [".txt", ".md", ".html"]:
        typer.echo(
            f"Error: Unsupported file type '{suffix}'. Supported: .txt, .md, .html"
        )
        raise typer.Exit(1)

    text = file_path.read_text(encoding="utf-8")
    if not text.strip():
        typer.echo("Error: Input file is empty.")
        raise typer.Exit(1)

    # Clean text based on type
    if suffix == ".html":
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()
    # For .txt and .md, keep as is

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Chunk text
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    # Set device
    if device == "cuda":
        if not torch.cuda.is_available():
            typer.echo("Warning: CUDA selected but not available. Falling back to CPU.")
            device = "cpu"
        else:
            device = 0  # Use first GPU
    elif device.isdigit():
        device = int(device)  # Allow specific GPU index
    else:
        device = "cpu"

    # Initialize pipeline
    try:
        pipe = pipeline("text-to-speech", model=model, device=device)
    except Exception as e:
        typer.echo(f"Error loading model '{model}': {e}. Try a different model.")
        raise typer.Exit(1)

    # Generate audio for each chunk
    audio_arrays = []
    sample_rates = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            result = pipe(chunk)
            audio_arrays.append(np.array(result["audio"]))
            sample_rates.append(result["sampling_rate"])
        except Exception as e:
            typer.echo(f"Error generating audio for chunk: {e}")
            continue

    if not audio_arrays:
        typer.echo("Error: No audio generated.")
        raise typer.Exit(1)

    # Check sample rates
    unique_rates = set(sample_rates)
    if len(unique_rates) > 1:
        typer.echo("Warning: Mismatched sample rates, resampling all to target rate.")
        target_rate = max(unique_rates)  # Use highest, or user specified?
        if sample_rate:
            target_rate = sample_rate
        else:
            target_rate = 24000  # Common TTS rate

        resampled_arrays = []
        for arr, rate in zip(audio_arrays, sample_rates):
            if rate != target_rate:
                import librosa

                arr = librosa.resample(arr, orig_sr=rate, target_sr=target_rate)
            resampled_arrays.append(arr)
        audio_arrays = resampled_arrays
        sample_rates = [target_rate] * len(audio_arrays)
    else:
        target_rate = next(iter(unique_rates))
        if sample_rate and sample_rate != target_rate:
            typer.echo(f"Resampling to user specified rate {sample_rate}.")
            import librosa

            audio_arrays = [
                librosa.resample(arr, orig_sr=target_rate, target_sr=sample_rate)
                for arr in audio_arrays
            ]
            target_rate = sample_rate

    # Concatenate
    concatenated = np.concatenate(audio_arrays)

    # Audio array is (1, samples), squeeze to (samples,)
    audio_data = concatenated.squeeze()

    # Write file
    ext = pathlib.Path(output).suffix.lower()
    if ext == ".wav":
        sf.write(output, audio_data, target_rate)
        typer.echo(f"Audio saved to {output}")
    elif ext == ".mp3":
        # Convert to mp3 using pydub
        # First write temp wav
        temp_wav = output.replace(".mp3", "_temp.wav")
        sf.write(temp_wav, audio_data, target_rate)
        audio = AudioSegment.from_wav(temp_wav)
        audio.export(output, format="mp3")
        os.remove(temp_wav)
        typer.echo(f"Audio saved to {output}")
    else:
        sf.write(output.replace(ext, ".wav"), audio_data, target_rate)
        typer.echo(f"Audio saved as .wav (unsupported format {ext})")


def main():
    typer.run(convert)


if __name__ == "__main__":
    main()
