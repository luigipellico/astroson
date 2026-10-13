import cv2
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

class HandTrackingEngine:
    """Motore di tracciamento mani e scheletro basato su MediaPipe"""
    def __init__(self, max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5):
        self.available = MEDIAPIPE_AVAILABLE
        if not self.available:
            return

        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process_frame(self, frame):
        """Elabora il frame BGR, disegna lo scheletro ed estrae la posizione della punta dell'indice"""
        if not self.available or frame is None:
            return frame, None

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        results = self.hands.process(image_rgb)
        
        image_rgb.flags.writeable = True
        processed_image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        hand_pos = None
        h, w, _ = processed_image.shape

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    processed_image,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(255, 143, 0), thickness=2, circle_radius=3),
                    self.mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                
                index_tip = hand_landmarks.landmark[8]
                cx, cy = int(index_tip.x * w), int(index_tip.y * h)
                cv2.circle(processed_image, (cx, cy), 12, (0, 255, 255), 2)
                cv2.circle(processed_image, (cx, cy), 4, (255, 255, 255), -1)
                
                hand_pos = (index_tip.x, index_tip.y)

        return processed_image, hand_pos