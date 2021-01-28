import os
import re
import yaml
import shutil
import argparse
import pandas as pd
from glob import glob
from moviepy.editor import clips_array, VideoFileClip, \
                        CompositeVideoClip, AudioFileClip
from biliwalle.waveweaver import empty_audio_clip


def load_config(configfn):
    with open(configfn) as fh:
        config = yaml.load(fh, Loader=yaml.Loader)

    data = config.get("data", {}) 
    audiodir = data.get("audiodir", "")
    videodir = data.get("videodir", "")
    outdir = data.get("outdir", "")
    protocolcsv = data.get("protocolcsv", "")
    assert os.path.exists(audiodir) is True, \
        "audiodir %s doesn't exist, please check"%audiodir
    assert os.path.exists(videodir) is True, \
        "videodir %s doesn't exist, please check"%videodir
    assert os.path.exists(protocolcsv) is True, \
        "protocolcsv %s doesn't exist, please check"%protocolcsv
    protocoldf = pd.read_csv(protocolcsv)
    video_setting = config.get("video_setting", {})
    saveconfig = config.get("other", {}).get("saveconfig", None)
    reprocess = config.get("other", {}).get("reprocess", True)
    return protocoldf, audiodir, videodir, outdir, \
           video_setting, saveconfig, reprocess


def compose(videos, audio, output_size,
            bg_color=(255, 255, 255)):
    v = CompositeVideoClip(videos, output_size,
                          bg_color=bg_color)
    if audio != None:
        v = v.with_audio(audio).subclip(0, audio.duration)
    return v


def center_to_topleft(center_x, center_y, width, height):
    x = center_x - width // 2
    y = center_y - height // 2
    return x, y


def process_video(videofn, resize_to_width, resize_to_height,
                  position_x, position_y):
    x, y = center_to_topleft(position_x, position_y, 
                             resize_to_width, resize_to_height)
    video = VideoFileClip(videofn)
    video = video.resize(width=resize_to_width, 
                        height=resize_to_height).\
                  with_position((x, y))
    return video


def process_audio(audiofn, audiodir, fps=44100):
    if "silence" not in audiofn.lower():
        n_audiofn = glob(audiodir+"*/%s"%audiofn)
        if not len(n_audiofn):
            raise Exception("\n\nSKIP WARNING: %s in not found in sub directory of %s"\
                    %(audiofn, audiodir))
        audio = AudioFileClip(n_audiofn[0])
    else:
        audiofn = audiofn.lower()
        silence_duraion = int(re.findall("([0-9]+)",
                                         audiofn)[0])  # in seconds
        audio = empty_audio_clip(silence_duraion*1000, 
                                      fps=fps)
    return audio


def make_clip_with_protocol(protocoldf, outdir, 
                             audiodir, videodir, video_setting,
                             test_identifier="Test_trial_ID",
                             train_identifier="Training_trial_ID",
                             fps=30,
                             codec='libx264',
                             verbose=1,
                             reprocess=True):
    '''
        Make movie based on the protocol table
    '''
    w = video_setting["out_width"]
    h = video_setting["out_height"]

    if not os.path.exists(outdir): os.makedirs(outdir)

    for _, row in protocoldf.iterrows():
        outname = os.path.join(outdir, row["Output_file"])

        if os.path.exists(outname) and (not reprocess):
            if verbose:
                print("\nSKIP found existing %s"%outname)
            continue
            
        if test_identifier in protocoldf.columns:
            # for testing movie making with left/right objects
            left_video_fn = glob(videodir+"/%s_*"%row["Left"])[0]
            right_video_fn = glob(videodir+"/%s_*"%row["Right"])[0]
            left_video = process_video(left_video_fn, 
                                **video_setting["objects"]["Left"])
            right_video = process_video(right_video_fn, 
                                **video_setting["objects"]["Right"])
            videos = [left_video, right_video]
        
        elif train_identifier in protocoldf.columns:
            # for training movie making with left/right objects
            video_fn = glob(videodir+"/%s_*"%row["Object"])[0]
            video = process_video(video_fn,
                            **video_setting["objects"]["Object"])
            videos = [video]
        
        else:
            raise Exception("Neither %s or %s can be found in the columns;\
                             Make sure you have the right protocol csv fomat"\
                             %(test_identifier, train_identifier))

        # process audio file
        audio = process_audio(row["Audio_file"], audiodir)
        # compose
        outvideo = compose(videos=videos,
                           audio=audio,
                           output_size=(w, h))

        if verbose:
            print("\nWriting to %s"%outname)
            logger = "bar"
        else:
            logger = None
        
        outvideo.write_videofile(outname, codec=codec,
                                 audio_codec='aac',
                                 remove_temp=True,
                                 fps=fps,
                                 logger=logger)
        
        # close the opened videos
        for v in videos:
            v.close()
        outvideo.close()
        audio.close()



def main():
    parser = argparse.ArgumentParser(description='Create stimuli video clips')
    parser.add_argument('-c', '--config', required=True,
           help="configuration file for concatenating audio files")
    parser.add_argument('-v', '--verbose', default=1, type=int,
           help="verbose level, 0 or 1")
    args = parser.parse_args()

    protocoldf, audiodir, videodir, outdir,\
         video_setting, saveconfig, reprocess\
             = load_config(args.config)
    make_clip_with_protocol(protocoldf, outdir, 
                             audiodir, videodir, video_setting,
                             verbose=bool(args.verbose),
                             reprocess=reprocess)
    if saveconfig:
        shutil.copy(args.config, outdir)

    
if __name__ == "__main__":
    main()
