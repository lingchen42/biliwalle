Welcome to BILI-WALLE!

This tool suite was developed to streamline the process of creating video stimuli files for an eye-tracking study. It was specifically developed for a Preferential Looking Paradigm but can be generalized to create other types of video files given a specific protocol. 

---
## Install Prerequisites
* XCODE (Mac only). This is the essential package for mac developer setup. - https://developer.apple.com/xcode/
* Git - https://git-scm.com/
* Python - https://www.python.org/downloads/

## Installation
```
pip install git+https://github.com/lingchen42/biliwalle.git --upgrade
#pip install git+https://github.com/lingchen42/biliwalle.git@{tagname} --upgrade  # install a certain release
```

## Usage
See biliwalle [Wiki](https://github.com/lingchen42/biliwalle/wiki)


## FAQ
* "RuntimeError: No ffmpeg exe could be found"
    * Download FFMPEG executable files of the corresponding system from https://ffmpeg.org/download.html
    * If you are using Linux/Mac, run export IMAGEIO_FFMPEG_EXE="PATH_TO_THE_DOWNLOADED_FFMPEG_EXECUTABLE" in your terminal before run any of the biliwalle commands.
