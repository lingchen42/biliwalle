import yaml
import argparse
import numpy as np
from glob import glob
import pandas as pd
from moviepy.editor import *
from moviepy.audio.AudioClip import AudioArrayClip


def load_config(configfn):
    with open(configfn) as fh:
        config = yaml.load(fh, Loader=yaml.Loader)

    data = config.get("data", {}) 
    audiodir = data.get("audiodir", "")
    protocolcsv = data.get("protocolcsv", "")
    assert os.path.exists(audiodir) is True, \
        "audiodir %s doesn't exist, please check"%audiodir
    assert os.path.exists(protocolcsv) is True, \
        "protocolcsv %s doesn't exist, please check"%protocolcsv
    protocoldf = pd.read_csv(protocolcsv)
    audiofiles = os.listdir(audiodir)
    audio_setting = config.get("audio_setting", {})
    return protocoldf, audiofiles, audiodir, audio_setting


def empty_audio_clip(duration, fps):
    empty_clip = np.zeros((fps*duration, 2))
    empty_clip = AudioArrayClip(empty_clip, fps=fps) 
    empty_clip.end = empty_clip.start + empty_clip.duration
    return empty_clip


def concatenate_audiofns(audiofns, audiodir,
                         start_padding, interval_padding,
                         end_padding, additional_padding=0,
                         additional_padding_location="start",
                         additional_padding_value_column=None,
                         fps=44100,
                         savetofn=False,
                         ):
    if additional_padding:
        if additional_padding_location == "start":
            start_padding += additional_padding
        elif additional_padding_location == "end":
            end_padding += additional_padding
        elif additional_padding_location == "middle":
            interval_padding += additional_padding
        
    audio_files = []
    last = len(audio_files) - 1
    current_start = 0
    for i, audiofn in enumerate(audiofns):
        audiofn = os.path.join(audiodir, audiofn)
        a = AudioFileClip(audiofn)

        if i != last:
            if (i==0) and (start_padding != 0):  # start padding
                start_clip = empty_audio_clip(duration=start_padding,
                                        fps=fps)
                audio_files.append(start_clip)
                current_start += start_clip.end
            second_padding = interval_padding
        else:
            second_padding = end_padding

        # audio
        audio_files.append(a.set_start(current_start))
        current_start += a.duration
        # add interval or end
        second_clip = empty_audio_clip(duration=second_padding,
                                    fps=fps)
        audio_files.append(second_clip.set_start(current_start))
        # update current_start
        current_start += second_clip.duration
        
    audio = CompositeAudioClip(audio_files)
    if savetofn:
        audio.write_audiofile(savetofn, fps=fps)

    return audio


def combine_with_protocol_table(protocoldf, outdir, audiodir, audio_setting,
                            fps=44100):
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    for key, grp in protocoldf.groupby(["Sentence_id", "Block",
                                     "Condition", "Word"]):
        grp = grp.sort_values("Sequence")
        audiofns = grp["File"].values
        outfn = os.path.join(outdir, grp["Filename"].values[0])
        audio_setting["additional_padding"] \
            = grp[audio_setting["additional_padding_value_column"]]\
                .values[0]
        try:
            concatenate_audiofns(audiofns, audiodir, fps=fps,
                        savetofn=outfn, **audio_setting)
        except OSError as e:
            print("\n\nWARNING: ", e)
            print("SKIP %s\n\n"%outfn)


def main():
    parser = argparse.ArgumentParser(description='Concatenate audio files')
    parser.add_argument('-c', '--config', required=True,
           help="configuration file for concatenating audio files")
    parser.add_argument('-o', '--outdir', required=True,
           help="output directory")
    args = parser.parse_args()

    protocoldf, audiofiles, audiodir, audio_setting = load_config(args.config)
    combine_with_protocol_table(protocoldf, args.outdir, audiodir, audio_setting)                            

    
if __name__ == "__main__":
    main()