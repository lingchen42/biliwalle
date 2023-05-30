import os
import yaml
import shutil
import argparse
import numpy as np
import pandas as pd
from moviepy.editor import *
from moviepy.audio.AudioClip import AudioArrayClip


def load_config(configfn):
    with open(configfn) as fh:
        config = yaml.load(fh, Loader=yaml.Loader)

    data = config.get("data", {}) 
    audiodir = data.get("audiodir", "")
    outdir = data.get("outdir", "")
    protocolcsv = data.get("protocolcsv", "")
    assert os.path.exists(audiodir) is True, \
        "audiodir %s doesn't exist, please check"%audiodir
    assert os.path.exists(protocolcsv) is True, \
        "protocolcsv %s doesn't exist, please check"%protocolcsv
    protocoldf = pd.read_csv(protocolcsv)
    audio_setting = config.get("audio_setting", {})
    saveconfig = config.get("other", {}).get("saveconfig", None)
    reprocess = config.get("other", {}).get("reprocess", True)
    return protocoldf, audiodir, outdir, \
           audio_setting, saveconfig, reprocess


def empty_audio_clip(duration, fps):
    '''
        duration is in ms
    '''
    empty_clip = np.zeros((int(fps*duration/1000), 2))
    empty_clip = AudioArrayClip(empty_clip, fps=fps) 
    empty_clip.end = empty_clip.start + empty_clip.duration
    return empty_clip


def concatenate_audiofns(audiofns, audiodir,
                         start_padding, interval_padding,
                         end_padding, additional_padding=0,
                         additional_padding_location="start",
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
        try:  # in moviepy 2.0
            audio_files.append(a.with_start(current_start))
        except: # moviepy 1.0
            audio_files.append(a.set_start(current_start))
        current_start += a.duration

        if second_padding:
            # add interval or end
            second_clip = empty_audio_clip(duration=second_padding,
                                        fps=fps)
            try:
                audio_files.append(second_clip.with_start(current_start))
            except:
                audio_files.append(second_clip.set_start(current_start))

            # update current_start
            current_start += second_clip.duration
        
    audio = CompositeAudioClip(audio_files)
    if savetofn:
        audio.write_audiofile(savetofn, fps=fps)

    try:
        audio.close()
        for a in audio_files:
            a.close()
    except Exception as e:
        print(e)

    return audio


def weave_audio_with_protocol(protocoldf, outdir, audiodir, audio_setting,
                              fps=44100, verbose=1, reprocess=True):
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
            if os.path.exists(outfn) and (not reprocess):
                if verbose:
                    print("\nSKIP found existing %s"%outfn)
                continue
            concatenate_audiofns(audiofns, audiodir, fps=fps,
                        savetofn=outfn, **audio_setting)
        except OSError as e:
            print("\n\nWARNING: ", e)
            print("SKIP %s\n\n"%outfn)


def main():
    parser = argparse.ArgumentParser(description='Concatenate audio files')
    parser.add_argument('-c', '--config', required=True,
           help="configuration file for concatenating audio files")
    args = parser.parse_args()

    protocoldf, audiodir, outdir,\
         audio_setting, saveconfig, reprocess\
              = load_config(args.config)
    weave_audio_with_protocol(protocoldf, outdir, audiodir, audio_setting,
                              reprocess=reprocess)
    if saveconfig:
        shutil.copy(args.config, outdir)

    
if __name__ == "__main__":
    main()
