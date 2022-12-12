import argparse
import configparser
import os
import time
import signal
from typing import List

import cv2

from Arducam import *
from ImageConvert import *

exit_ = False
save_ = False


def sigint_handler(signum, frame):
    global exit_
    exit_ = True


signal.signal(signal.SIGINT, sigint_handler)
signal.signal(signal.SIGTERM, sigint_handler)


def display_fps(index):
    display_fps.frame_count[index] += 1

    current = time.time()
    if current - display_fps.start >= 1:
        print(f"fps: {display_fps.frame_count}")
        display_fps.frame_count = [0] * len(display_fps.frame_count)
        display_fps.start = current


display_fps.start = time.time()
# display_fps.frame_count = 0


def get_config_file(base_path, cfg, serial):
    if serial not in cfg["serials"]:
        raise RuntimeError(f"Config not found for camera {serial}.")

    profile = cfg["serials"].get(serial)
    cam_cfg = cfg[profile].get("file")
    order = cfg[profile].get("order")

    path = os.path.join(base_path, cam_cfg)
    return path, order


def flush_cameras(cameras):
    for camera in cameras:
        ArducamSDK.Py_ArduCam_flush(camera.handle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config-file', type=str, required=True, help='Specifies the configuration file.')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Output device information.')
    parser.add_argument('--preview-width', type=int, required=False, default=-1, help='Set the display width')
    parser.add_argument('-n', '--nopreview', action='store_true', required=False, help='Disable preview windows.')
    parser.add_argument('-t', '--target-fps', type=int, required=False, default=10, help='Target FPS to determine frame grab timeouts')
    
    ## Setup arguments
    args = parser.parse_args()
    config_file: str = args.config_file
    verbose: bool = args.verbose
    preview_width: int = args.preview_width
    no_preview: bool = args.nopreview
    target_fps: int = args.target_fps

    ## Parse meta-config file
    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.read(config_file)
    base_path = os.path.dirname(config_file)

    ## Scan for devices
    devices_num,index,serials = ArducamSDK.Py_ArduCam_scan()
    print("Found %d devices"%devices_num)

    serial_strings = []
    for i in range(devices_num):
        datas = serials[i]
        serial = "%c%c%c%c-%c%c%c%c-%c%c%c%c"%(datas[0],datas[1],datas[2],datas[3],
                                            datas[4],datas[5],datas[6],datas[7],
                                            datas[8],datas[9],datas[10],datas[11])
        serial_strings.append(serial)
        print("Index:",index[i],"Serial:",serial)

    ## Open all cameras
    cameras = []
    orders = []
    for i in range(devices_num):
        camera = ArducamCamera()

        # find correct config
        serial = serial_strings[i]
        cam_cfg, order = get_config_file(base_path, config, serial)
        print(cam_cfg, order)

        retry_count = 0
        while not camera.openCamera(cam_cfg, index=i):
            retry_count += 1
            time.sleep(1)
            if retry_count == 10:
                raise RuntimeError("Failed to open camera.")

        if verbose:
            camera.dumpDeviceInfo()

        camera.start()
        # camera.setCtrl("setFramerate", 2)
        camera.setCtrl("setExposureTime", 30000)
        camera.setCtrl("setAnalogueGain", 1)
        ArducamSDK.Py_ArduCam_flush(camera.handle)
        cameras.append(camera)
        orders.append(order)

    ## Run main loop
    display_fps.frame_count = [0] * devices_num
    scale_width = preview_width
    saved_frames: List[List[np.ndarray]] = []
    total_saved = 0
    count_timeout = 0
    it_count = 0

    cameras = [c for o, c in sorted(zip(orders, cameras), key=lambda pair: pair[0])]
    flush_cameras(cameras)

    cv2.namedWindow("Arducam0")

    while not exit_:
        current_frames: List[np.ndarray] = []
        availables = []

        for i, camera in enumerate(cameras):
            ret, data, cfg, available_before = camera.read(timeout=1000./target_fps)
            availables.append(available_before)
            # print(f'[cam {i}] available: {available_before}')

            if ret:
                image = convert_image(data, cfg, camera.color_mode)
                current_frames.append(image)
                display_fps(i)

            else:
                print(".", end='')
                count_timeout += 1
                if count_timeout > 50:
                    print()
                    count_timeout = 0
                break

        if len(current_frames) == devices_num:
            print(f"Available: {availables}")
            it_count += 1

            if save_ and it_count % 5 == 0:
                saved_frames.append(current_frames)

            if not no_preview:
                for i, frame in enumerate(current_frames):
                    if scale_width != -1:
                        scale = scale_width / frame.shape[0]
                        frame = cv2.resize(frame, None, fx=scale, fy=scale)
                        # print(stitched_image.shape)

                    cv2.imshow(f"Arducam{i}", frame)

        elif len(current_frames) > 0:
            print(f'Readout desync -- read {len(current_frames)}/{devices_num} cameras')
            print('FIFOs should be flushed to resync')

        key = cv2.waitKey(1)
        if key == ord('q'):
            exit_ = True
        elif key == ord('s'):
            save_ = True
        elif key == ord('c'):
            it_count = 0
            save_ = False
            for frame_set in saved_frames:
                os.makedirs(f"images/image{total_saved}/", exist_ok=True)
                for i, frame in enumerate(frame_set):
                    cv2.imwrite(f"images/image{total_saved}/camera{i}.bmp", frame)
                total_saved += 1
            saved_frames = []
        elif key == ord('f'):
            flush_cameras(cameras)
            it_count = 0

    for camera in cameras:
        camera.stop()
        camera.closeCamera()
