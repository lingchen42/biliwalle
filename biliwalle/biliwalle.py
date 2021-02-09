import os
import re
import yaml
import shutil
import tempfile
import argparse
import pandas as pd
from tqdm import tqdm
from PIL import Image, ImageDraw
from moviepy.editor import VideoFileClip, ImageClip,\
                           concatenate_videoclips
import warnings
warnings.filterwarnings("ignore")


def load_config(configfn):
    with open(configfn) as fh:
        config = yaml.load(fh, Loader=yaml.Loader)
    data = config.get("data", {}) 
    videodir = data.get("videodir", "")
    outdir = data.get("outdir", "")
    video_setting = config.get("video_setting", {})
    protocolcsv = data.get("protocolcsv", "")
    protocoldf = pd.read_csv(protocolcsv)
    saveconfig = config.get("other", {}).get("saveconfig", None)
    reprocess = config.get("other", {}).get("reprocess", True)
    return videodir, outdir, protocoldf, saveconfig,\
           video_setting, config, reprocess


def blank_clip(duration, bg_color, size):
    '''
        create a blank clip
    '''
    # temp dir
    dirpath = tempfile.mkdtemp()
    img = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(img) 
    imgpath = os.path.join(dirpath, "blank.png")
    img.save(imgpath)
    clip = ImageClip(imgpath).\
            with_duration(duration)

    # remove temp dir
    shutil.rmtree(dirpath)

    return clip


def make_movie_with_protocol(protocoldf,
                             outdir,
                             videodir,
                             video_setting,
                             order_col="Order",
                             video_file_col="Video_file",
                             trial_type_col="Trial_type",
                             outname_col="Output_video_file",
                             fps=30,
                             codec='libx264',
                             color_dict={
                                 "black": (0, 0, 0),
                                 "white": (255, 255, 255)
                             },
                             verbose=1,
                             reprocess=True):

    w = video_setting["out_width"]
    h = video_setting["out_height"]
    between_trial = video_setting.get("between_trial", None)
    between_trial_duration = between_trial["duration"]
    between_trial_bgcolor = between_trial["bg_color"]

    if not os.path.exists(outdir): os.makedirs(outdir)

    for order, grp in protocoldf.groupby(order_col):
        videos = [] 
        outname = grp[outname_col].values[0]
        outname = os.path.join(outdir, outname)

        if os.path.exists(outname) and (not reprocess):
            if verbose:
                print("\n\n")
                print("#"*80)
                print("\nSKIP found existing %s\n"%outname)
            continue
        
        if verbose:
            print("\n\n")
            print("#"*80)
            print("Generating %sth file to %s\n"%(int(order), outname))

        for _, row in tqdm(grp.iterrows()):
            videofn = row[video_file_col]
            trial_type = row[trial_type_col]

            if trial_type.lower() == "transition":
                # expect to see videofn color_[0-9]s
                bg_color, duration = videofn.split("_")
                duration = int(re.findall("([0-9]*)s", duration)[0])
                video = blank_clip(duration, bg_color.lower(), size=(w,h))
                videos.append(video)
            else:
                videofn = os.path.join(videodir, videofn)
                if os.path.exists(videofn):
                    video = VideoFileClip(videofn)
                    videos.append(video)
                    # between trial interval
                    interval_video = blank_clip(between_trial_duration, 
                            between_trial_bgcolor.lower(), size=(w,h))
                    videos.append(interval_video)
                else:
                    print("SKIP %s doesn't exist"%videofn)
                    continue

        outvideo = concatenate_videoclips(videos)
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


def main():
    parser = argparse.ArgumentParser(description='Compose stimuli movie')
    parser.add_argument('-c', '--config', required=True,
           help="configuration file for concatenating audio files")
    parser.add_argument('-v', '--verbose', default=1, type=int,
           help="verbose level, 0 or 1")
    args = parser.parse_args()
    
    videodir, outdir, protocoldf, saveconfig, video_setting,\
        config, reprocess = \
        load_config(args.config)
    make_movie_with_protocol(protocoldf,
                             outdir,
                             videodir,
                             video_setting,
                             verbose=args.verbose,
                             reprocess=reprocess)

    if saveconfig:
        shutil.copy(args.config, outdir)

    
if __name__ == "__main__":
    main()
