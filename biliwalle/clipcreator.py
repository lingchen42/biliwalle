import os
import re
import yaml
import shutil
import argparse
import mimetypes
import pandas as pd
from glob import glob
from moviepy.editor import ImageClip, VideoFileClip, \
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
        try:
            v = v.with_audio(audio).subclip(0, audio.duration)
        except:
            v = v.set_audio(audio).subclip(0, audio.duration)
    return v


def center_to_topleft(center_x, center_y, width, height):
    x = center_x - width // 2
    y = center_y - height // 2
    return x, y


def check_image_or_video(fn):
    t = mimetypes.guess_type(fn)[0]
    if t.startswith('video'):
        return 'video'
    elif t.startswith('image'):
        return 'image'
    else:
        raise Exception('File %s is not video or image, please double check'%fn)


def image_to_video(imagefn, duration):
    '''
    imagefn: Any picture file (png, tiff, jpeg, etc.) as a string or a path-like object
    '''
    clip = ImageClip(imagefn).set_duration(duration)
    return clip


def process_video(fn, resize_to_width, resize_to_height,
                  position_x, position_y, duration=None):
    x, y = center_to_topleft(position_x, position_y, 
                             resize_to_width, resize_to_height)
    fn_type = check_image_or_video(fn)
    if fn_type == 'video':
        video = VideoFileClip(fn)
    else:
        video = image_to_video(fn, duration=duration)
    try:
        video = video.resize(width=resize_to_width, 
                        height=resize_to_height).\
                     with_position((x, y))
    except:
        video = video.resize(width=resize_to_width, 
                        height=resize_to_height).\
                     set_position((x, y))
    return video


def process_audio(audiofn, audiodir, fps=44100):
    if "silence" not in audiofn.lower():
        n_audiofn = glob(audiodir+audiofn)
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
    bg_color = video_setting.get("bg_color", [255, 255, 255])
    bg_color = tuple(bg_color)
    assert len(bg_color) == 3,\
        "Please provide bg_color in RGB format in the config, such as [255, 255, 255]"

    if not os.path.exists(outdir): os.makedirs(outdir)

    for _, row in protocoldf.iterrows():
        outname = os.path.join(outdir, row["Output_file"])
        
        # process audio file
        audio = process_audio(row["Audio_file"], audiodir)
        duration = audio.duration

        if os.path.exists(outname) and (not reprocess):
            if verbose:
                print("\nSKIP found existing %s"%outname)
            continue
            
        if test_identifier in protocoldf.columns:
            # for testing movie making with left/right objects
            p = videodir+"/%s*"%row["Left"]
            left_video_fns = glob(p)
            assert len(left_video_fns) == 1, \
                f"File pattern {p} is found {len(left_video_fns)} times, please make sure it's unique" 
            left_video_fn = left_video_fns[0]

            p = videodir+"/%s*"%row["Right"]
            right_video_fns = glob(p)
            assert len(right_video_fns) == 1, \
                f"File pattern {p} is found {len(right_video_fns)} times, please make sure it's unique" 
            right_video_fn = right_video_fns[0]

            left_video = process_video(left_video_fn, duration=duration,
                                **video_setting["objects"]["Left"])
            right_video = process_video(right_video_fn, duration=duration,
                                **video_setting["objects"]["Right"])
            videos = [left_video, right_video]
        
        elif train_identifier in protocoldf.columns:
            # for training movie making with center object
            p = videodir+"/%s_*"%row["Object"]
            video_fns = glob(p)
            assert len(video_fns) == 1, \
                f"File pattern {p} is found {len(video_fns)} times, please make sure it's unique"
            video_fn = video_fns[0]

            video = process_video(video_fn, duration=duration,
                            **video_setting["objects"]["Object"])
            videos = [video]
        
        else:
            raise Exception("Neither %s or %s can be found in the columns;\
                             Make sure you have the right protocol csv fomat"\
                             %(test_identifier, train_identifier))

        # compose
        outvideo = compose(videos=videos,
                           audio=audio,
                           output_size=(w, h),
                           bg_color=bg_color)

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
