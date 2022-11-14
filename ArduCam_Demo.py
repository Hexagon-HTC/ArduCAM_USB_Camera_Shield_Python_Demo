import argparse
import time
import signal
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

    ## Scan for devices
    devices_num,index,serials = ArducamSDK.Py_ArduCam_scan()
    print("Found %d devices"%devices_num)
    for i in range(devices_num):
        datas = serials[i]
        serial = "%c%c%c%c-%c%c%c%c-%c%c%c%c"%(datas[0],datas[1],datas[2],datas[3],
                                            datas[4],datas[5],datas[6],datas[7],
                                            datas[8],datas[9],datas[10],datas[11])
        print("Index:",index[i],"Serial:",serial)

    ## Open all cameras
    cameras = []
    for i in range(devices_num):
        camera = ArducamCamera()

        if not camera.openCamera(config_file, index=i):
            raise RuntimeError("Failed to open camera.")

        if verbose:
            camera.dumpDeviceInfo()

        camera.start()
        # camera.setCtrl("setFramerate", 2)
        # camera.setCtrl("setExposureTime", 20000)
        # camera.setCtrl("setAnalogueGain", 800)
        ArducamSDK.Py_ArduCam_flush(camera.handle)
        cameras.append(camera)

    ## Run main loop
    display_fps.frame_count = [0] * devices_num
    scale_width = preview_width
    saved_frames = []
    total_saved = 0
    count_timeout = 0
    it_count = 0

    while not exit_:
        current_frames = []

        for i, camera in enumerate(cameras):
            ret, data, cfg, available_before = camera.read(timeout=1000./target_fps)
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
            it_count += 1
            stitched_image = np.concatenate(current_frames, axis=0)

            if save_ or it_count % 5 == 0:
                saved_frames.append(stitched_image)

            if scale_width != -1:
                scale = scale_width / stitched_image.shape[1]
                stitched_image = cv2.resize(stitched_image, None, fx=scale, fy=scale)
                # print(stitched_image.shape)

            if not no_preview:
                cv2.imshow("Arducam", stitched_image)

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
            for frame in saved_frames:
                cv2.imwrite(f"images/image{total_saved}.bmp", frame)
                total_saved += 1
            saved_frames = []

    for camera in cameras:
        camera.stop()
        camera.closeCamera()
