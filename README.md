# Introduction

Substance 3D Painter synchronization UE plugin<br>

## Function Introduction
●Seamless Integration:
Through the plug-in, assets in Substance Painter can be synchronized to Unreal Engine with one click, reducing manual operations and intermediate steps.
<img src="doc/1.gif" width="600" alt="示例图片">

●Real-time Viewport Synchronization:
Real-time synchronization between Substance Painter and Unreal Engine viewports is achieved, and artists can directly view the effects in the engine, improving work efficiency.
<img src="doc/2.gif" width="600" alt="示例图片">

●Automation and Flexibility:
Supports automatic creation of materials and synchronization of maps, and provides flexible output path settings and material configuration options to meet the needs of different projects.
<img src="doc/3.gif" width="600" alt="示例图片">

## Video Demonstration
[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/K-tsUKiZ9qc/0.jpg)](https://www.youtube.com/watch?v=K-tsUKiZ9qc)<br>

## Features
- Output textures according to presets
- Save corresponding paths in the engine
- Automatically output models
- Automatically create materials
- Automatically assemble models
- One-click synchronization of textures
- Synchronize viewports
- UDIM support

## Installation
- UE menu 
  Edit>Editor Preferences>Use Less CPU when in Background > Uncheck
  Edit>Project Settings>Python Remote Execution>Enable Remote Execution > Check
  
  UDIM support
  Edit>Project Settings>Engine>Rendering>Enable virtual texture support Check
  Edit>Project Settings>Engine>Rendering>Enable virtual texture for Opacity Mask Check

- Copy it to this "C:\Users\username\Documents\Adobe\Adobe Substance 3D Painter\python\plugins" directory

#### Version requirements</br>
  Substanc 3d Painter 10.1</br>
  Unreal 5.4 (theoretically 5.x and above are all supported but not tested)</br>

#### UE settings</br>
a. Turn off the Use Less CPU when in Background option in Editor Preferences to prevent UE from freezing when synchronizing the viewport.</br>
<img src="doc/4.png" width="600" alt="示例图片"></br>


b. Turn on Enable Remote Execution in Project Settings to support remote execution of Python scripts.</br>
<img src="doc/5.png" width="600" alt="示例图片"></br>

c. If UDIM support is required, you need to turn on Enable virtual texture support and Enable virtual textures for Opacity Mask under Project Settings->Rendering to support virtual textures.</br>
<img src="doc/6.png" width="600" alt="示例图片"></br>

### SP settings</br>
a. Python>Plugins Folder to open the python plugin directory.</br>
<img src="doc/7.png" width="600" alt="示例图片"></br>

b. Unzip to the Plugins directory and restart SP.</br>
<img src="doc/8.png" width="600" alt="示例图片"></br>

c. Make sure SPsync is enabled.</br>
<img src="doc/9.png" width="600" alt="示例图片"></br>
<img src="doc/10.png" width="600" alt="示例图片"></br>

d. Plugin window</br>
<img src="doc/11.png" width="600" alt="示例图片"></br>


## Contact
- Email    : yangskin@163.com
- BiliBili : https://space.bilibili.com/249466



