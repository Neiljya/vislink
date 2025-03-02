import cv2
import mediapipe as mp
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import numpy as np
import matplotlib.pyplot as plt

from Rotation2Vector import RotationVector, SensitivityParams, rot2MouseVector
from MouseAction import Mouse

MODEL_PATH = "face_landmarker.task"
LEFT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_LANDMARKS = [263, 387, 385, 362, 380, 373]

#eye landmarks needed to calculate EAR
# Define eye landmarks
LEFT_EYE_LANDMARKS = {"top": 159, "bottom": 145, "outer": 133, "inner": 33}
RIGHT_EYE_LANDMARKS = {"top": 386, "bottom": 374, "outer": 362, "inner": 263}
#MAX_EYE_LANDMARK = max(max(LEFT_EYE_LANDMARKS), max(RIGHT_EYE_LANDMARKS)) + 1
EAR_THRESHOLD = 0.25  # Adjust based on testing

# Helper functions
#-------------------------------------------------------------------------------


import cv2
import numpy as np
from mediapipe.framework.formats import landmark_pb2
from mediapipe import solutions

# Define eye landmarks
LEFT_EYE_LANDMARKS = {"top": 159, "bottom": 145, "outer": 133, "inner": 33}
RIGHT_EYE_LANDMARKS = {"top": 386, "bottom": 374, "outer": 362, "inner": 263}
EAR_THRESHOLD = 0.2  # Blink detection threshold

# Function to compute EAR
def calculate_EAR(landmarks, eye):
    """Computes Eye Aspect Ratio (EAR)"""
    top = np.array([landmarks[eye["top"]].x, landmarks[eye["top"]].y])
    bottom = np.array([landmarks[eye["bottom"]].x, landmarks[eye["bottom"]].y])
    outer = np.array([landmarks[eye["outer"]].x, landmarks[eye["outer"]].y])
    inner = np.array([landmarks[eye["inner"]].x, landmarks[eye["inner"]].y])

    vertical_dist = np.linalg.norm(top - bottom)
    horizontal_dist = np.linalg.norm(outer - inner)

    ear = vertical_dist / horizontal_dist
    return ear

def draw_landmarks_on_image(rgb_image, detection_result):
  face_landmarks_list = detection_result.face_landmarks
  annotated_image = np.copy(rgb_image)

  # Loop through the detected faces to visualize.
  for idx in range(len(face_landmarks_list)):
    face_landmarks = face_landmarks_list[idx]

    # Draw the face landmarks.
    face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
    face_landmarks_proto.landmark.extend([
      landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in face_landmarks
    ])

    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=solutions.face_mesh.FACEMESH_TESSELATION,
        landmark_drawing_spec=None,
        connection_drawing_spec=solutions.drawing_styles
        .get_default_face_mesh_tesselation_style())
    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=solutions.face_mesh.FACEMESH_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=solutions.drawing_styles
        .get_default_face_mesh_contours_style())
    solutions.drawing_utils.draw_landmarks(
        image=annotated_image,
        landmark_list=face_landmarks_proto,
        connections=solutions.face_mesh.FACEMESH_IRISES,
          landmark_drawing_spec=None,
          connection_drawing_spec=solutions.drawing_styles
          .get_default_face_mesh_iris_connections_style())

  return annotated_image

# Function to draw landmarks, lines, and EAR
def display_EAR(rgb_image, detection_result):
    face_landmarks_list = detection_result.face_landmarks
    annotated_image = np.copy(rgb_image)

    for face_landmarks in face_landmarks_list:
        h, w, _ = annotated_image.shape  # Image dimensions

        for eye in [LEFT_EYE_LANDMARKS, RIGHT_EYE_LANDMARKS]:
            # Get landmark coordinates
            top = (int(face_landmarks[eye["top"]].x * w), int(face_landmarks[eye["top"]].y * h))
            bottom = (int(face_landmarks[eye["bottom"]].x * w), int(face_landmarks[eye["bottom"]].y * h))
            outer = (int(face_landmarks[eye["outer"]].x * w), int(face_landmarks[eye["outer"]].y * h))
            inner = (int(face_landmarks[eye["inner"]].x * w), int(face_landmarks[eye["inner"]].y * h))

            # Draw vertical line (green) - between top and bottom eyelid
            cv2.line(annotated_image, top, bottom, (0, 255, 0), 2)

            # Draw horizontal line (blue) - between inner and outer eye corners
            cv2.line(annotated_image, inner, outer, (255, 0, 0), 2)

            # Draw eye landmarks as yellow dots
            for point in [top, bottom, outer, inner]:
                cv2.circle(annotated_image, point, 4, (0, 255, 255), -1)

        # Compute and display EAR
        left_ear = calculate_EAR(face_landmarks, LEFT_EYE_LANDMARKS)
        right_ear = calculate_EAR(face_landmarks, RIGHT_EYE_LANDMARKS)
        avg_ear = (left_ear + right_ear) / 2

        # Display EAR on the screen
        cv2.putText(annotated_image, f"EAR: {avg_ear:.2f}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # Blink detection message
        if avg_ear < EAR_THRESHOLD:
            cv2.putText(annotated_image, "BLINK DETECTED", (30, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    return annotated_image



def get_euler_angles(detection_result):
    matrices = detection_result.facial_transformation_matrixes
    if (matrices == None or len(matrices) == 0):
       return 0,0,0
    facial_transformation_matrix = detection_result.facial_transformation_matrixes[0]
    # Convert the 4x4 transformation matrix to a 3x3 rotation matrix
    rotation_matrix = np.array((facial_transformation_matrix).reshape(4, 4))[:3, :3]

    # Decompose the rotation matrix into Euler angles (roll, pitch, yaw)
    pitch, yaw, roll = cv2.RQDecomp3x3(rotation_matrix)[0]
    return roll, -pitch, yaw

# Function to compute EAR
def calculate_EAR(landmarks, eye):
    """Computes Eye Aspect Ratio (EAR)"""
    top = np.array([landmarks[eye["top"]].x, landmarks[eye["top"]].y])
    bottom = np.array([landmarks[eye["bottom"]].x, landmarks[eye["bottom"]].y])
    outer = np.array([landmarks[eye["outer"]].x, landmarks[eye["outer"]].y])
    inner = np.array([landmarks[eye["inner"]].x, landmarks[eye["inner"]].y])

    vertical_dist = np.linalg.norm(top - bottom)
    horizontal_dist = np.linalg.norm(outer - inner)

    ear = vertical_dist / horizontal_dist
    return ear

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    print("Initialized camera")

    # Creating Face Landmarker Object
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(base_options=base_options,
                                        output_face_blendshapes=True,
                                        output_facial_transformation_matrixes=True,
                                        num_faces=1)
    detector = vision.FaceLandmarker.create_from_options(options)
    print("Created Face landmarker")

    sensitivity = SensitivityParams(1, .05) # set sensitivity and deadzone
    mouse = Mouse()

    while cap.isOpened():
        success, img = cap.read()

        if not success:
           break
        mp_image = mp.Image(image_format= mp.ImageFormat.SRGB, data=cv2.flip(img, 1))

        start = time.time()

        detection_result = detector.detect(mp_image)
        print(detection_result)
        roll, pitch, yaw = get_euler_angles(detection_result)
        rotation = RotationVector(roll, pitch, yaw)
        mouseVector = rot2MouseVector(rotation, sensitivity)
        mouse.moveCursor(mouseVector)
        # print(len(detection_result.face_landmarks))
        annotated_image = draw_landmarks_on_image(mp_image.numpy_view(), detection_result)
        image_with_ear = display_EAR(annotated_image, detection_result)

        cv2.imshow("test", image_with_ear)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
