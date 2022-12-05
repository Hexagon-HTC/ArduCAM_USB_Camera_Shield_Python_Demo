# Instructions

## Install USB Driver

### Linux

Execute the installation script to set udev rules. so that the system can recognize the USB device.

1. [Download Script](https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield/releases/download/install_drivers/configure_udev_rules.sh)
2. Execute the following command:
```
chmod +x ./configure_udev_rules.sh
./configure_udev_rules.sh
```

**Note: After configuring the udev rules, you need to replug the device or restart the PC, otherwise you still need `sudo` to run the program.**

### Windows

1. [Download Driver](https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield/releases/download/install_drivers/install_USB_Camera_Drivers.zip)
2. Unzip the package.
3. Double-click the install_Drivers.bat file in the execution package.

## Install dependencies

### Arducam Library
```
python3 -m pip install -U pip
python3 -m pip install arducam_config_parser ArducamSDK
```
### OpenCV
```
python3 -m pip install opencv-python numpy
```
**Note: For Jetson no need to install OpenCV dependencies**

## Download Code
```shell
git clone https://github.com/Hexagon-HTC/ArduCAM_USB_Camera_Shield_Python_Demo.git
cd ArduCAM_USB_Camera_Shield_Python_Demo
git checkout multicam
```

## Run the Demo
```shell
python3 ArduCam_Demo.py -v --preview-width 1280 --target-fps 15 -f <path for camera cfg>
```
## Parameters
- -v: Whether to display camera information.
- --preview-width: Sets the width of the preview screen.
- --target-fps: Sets internal timeouts for frame waiting -- set it to slightly less than expected FPS
- -f: Specify the meta config file.

## Meta-configuration file syntax
```ini
[DEFAULT]
base_path = .

[profiles]
profile1 = ${base_path}/my/cam/type/camera_config_file1.cfg
profile2 = ${base_path}/my/cam/type/camera_config_file2.cfg

[serials]
ABCD-1234-1234 = profile1
ABCD-5678-5678 = profile2
```

**Note: The camera configuration files referenced inside the profiles can be found here: [ArduCAM_USB_Camera_Shield](https://github.com/ArduCAM/ArduCAM_USB_Camera_Shield/tree/master/Config)**

## Example
```shell
python3 ArduCam_Demo.py -v --preview-width 1280 --target-fps 15 -f camera_config/multicam_config.cfg
```

