"""Run an Argos CTranslate2 model without Stanza or network-dependent resources."""
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

def unpack_runtime(archive_path, destination):
    """Extract only the local inference files, reusing unchanged model packages."""
    destination = Path(destination)
    with zipfile.ZipFile(archive_path) as archive:
        metadata_name = next(n for n in archive.namelist() if PurePosixPath(n).name == 'metadata.json')
        prefix = str(PurePosixPath(metadata_name).parent)
        prefix = '' if prefix == '.' else prefix + '/'
        metadata = json.loads(archive.read(metadata_name))
        if metadata.get('from_code') != 'en' or metadata.get('to_code') != 'ru':
            raise ValueError('The model must translate from English to Russian.')
        selected = []
        for info in archive.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            relative = info.filename[len(prefix):]
            if relative == 'sentencepiece.model' or relative.startswith('model/'):
                parts = PurePosixPath(relative).parts
                if '..' in parts or PurePosixPath(relative).is_absolute():
                    raise ValueError('Invalid path inside model archive.')
                selected.append((info, relative))
        if not {'sentencepiece.model', 'model/model.bin'}.issubset({r for _, r in selected}):
            raise ValueError('Model package lacks CTranslate2 or SentencePiece files.')
        signature = hashlib.sha256(json.dumps([(i.filename,i.CRC,i.file_size)
                                               for i,_ in selected]).encode()).hexdigest()
        marker = destination / 'package.sha256'
        ready = marker.exists() and marker.read_text() == signature
        if ready and all((destination / r).is_file() and (destination / r).stat().st_size == i.file_size
                         for i,r in selected):
            return destination, metadata
        for info, relative in selected:
            target = destination.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + '.part')
            try:
                with archive.open(info) as source, partial.open('wb') as handle:
                    shutil.copyfileobj(source, handle)
                partial.replace(target)
            finally:
                partial.unlink(missing_ok=True)
        marker.write_text(signature)
        return destination, metadata

def split_token_batches(text, tokenizer, limit=180):
    """Use local punctuation rules and retain all tokens in unusually long sentences."""
    batches = []
    for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])|\n+', text.strip()):
        tokens = tokenizer.encode(sentence, out_type=str)
        batches.extend(tokens[start:start + limit] for start in range(0, len(tokens), limit))
    return batches

class OfflineTranslator:
    def __init__(self, directory, metadata):
        try:
            import ctranslate2
            import sentencepiece
        except ImportError as error:
            raise RuntimeError('Translation dependencies missing. Run with --install once.') from error
        self.tokenizer = sentencepiece.SentencePieceProcessor(model_file=str(directory / 'sentencepiece.model'))
        self.engine = ctranslate2.Translator(str(directory / 'model'), device='cpu',
                                           compute_type='int8', inter_threads=1, intra_threads=4)
        self.prefix = metadata.get('target_prefix', '')

    def __call__(self, text):
        if not text.strip():
            return text
        batches = split_token_batches(text, self.tokenizer)
        results = self.engine.translate_batch(
            batches, target_prefix=[[self.prefix]] * len(batches) if self.prefix else None,
            beam_size=4, num_hypotheses=1, replace_unknowns=True,
            length_penalty=0.2, max_input_length=0, max_decoding_length=512,
            max_batch_size=16)
        translated = []
        for result in results:
            value = self.tokenizer.decode(result.hypotheses[0])
            if self.prefix and value.startswith(self.prefix):
                value = value[len(self.prefix):]
            translated.append(value.strip())
        return ' '.join(translated)

def create_translator(archive_path, destination):
    directory, metadata = unpack_runtime(archive_path, destination)
    return OfflineTranslator(directory, metadata)
