import cv2
import mediapipe as mp
import pyautogui
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Inicializando o Mediapipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_drawing = mp.solutions.drawing_utils

# Inicializando controle de volume
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

# Função para calcular a distância entre dois pontos
def calculate_distance(point1, point2):
    return math.sqrt((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2)

# Função para detectar qual mão está sendo usada (direita ou esquerda)
def detect_hand_type(hand_landmarks):
    wrist = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
    index_finger_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
    if wrist.x < index_finger_mcp.x:
        return 'Right'
    else:
        return 'Left'

# Função para verificar se um ponto está dentro de um retângulo
def is_point_in_rectangle(point, top_left, bottom_right):
    return top_left[0] <= point[0] <= bottom_right[0] and top_left[1] <= point[1] <= bottom_right[1]

# Variáveis para armazenar a última posição do dedo e a posição inicial do mouse
last_finger_x, last_finger_y = None, None
mouse_down = False

# Coordenadas do quadrado na tela (top_left e bottom_right)
top_left = (100, 100)
bottom_right = (300, 300)

# Captura de vídeo
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Invertendo o frame horizontalmente para que a direção seja correta
    frame = cv2.flip(frame, 1)

    # Convertendo o frame para RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    # Desenhando o quadrado na tela
    cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Detectar o tipo de mão (direita ou esquerda)
            hand_type = detect_hand_type(hand_landmarks)

            # Obtendo a posição dos dedos
            index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
            middle_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
            middle_finger_dip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_DIP]

            # Convertendo as coordenadas normalizadas para coordenadas de pixel
            index_finger_tip_coords = (int(index_finger_tip.x * frame.shape[1]), int(index_finger_tip.y * frame.shape[0]))
            thumb_tip_coords = (int(thumb_tip.x * frame.shape[1]), int(thumb_tip.y * frame.shape[0]))

            if hand_type == 'Left':
                # Calculando a distância entre o dedo indicador e o polegar
                distance = calculate_distance(index_finger_tip, thumb_tip)

                # Se a distância for menor que um certo limiar, mover o mouse
                if distance < 0.05:  # Ajuste esse valor conforme necessário
                    if last_finger_x is None or last_finger_y is None:
                        last_finger_x, last_finger_y = index_finger_tip.x, index_finger_tip.y

                    # Calcular o deslocamento do dedo
                    dx = index_finger_tip.x - last_finger_x
                    dy = index_finger_tip.y - last_finger_y

                    # Atualizar a posição do dedo
                    last_finger_x, last_finger_y = index_finger_tip.x, index_finger_tip.y

                    # Obter a posição atual do mouse
                    mouse_x, mouse_y = pyautogui.position()

                    # Calcular a nova posição do mouse
                    screen_width, screen_height = pyautogui.size()
                    new_mouse_x = mouse_x + dx * screen_width
                    new_mouse_y = mouse_y + dy * screen_height

                    # Mover o mouse
                    pyautogui.moveTo(new_mouse_x, new_mouse_y)
                    mouse_down = True
                else:
                    mouse_down = False

                # Verificando se o dedo médio está abaixado (comparando com a base da palma)
                middle_finger_down = middle_finger_tip.y > middle_finger_dip.y + 0.02

                if middle_finger_down and mouse_down:
                    pyautogui.click()
                    mouse_down = False

            elif hand_type == 'Right':
                # Verificar se a mão está dentro do quadrado
                if is_point_in_rectangle(index_finger_tip_coords, top_left, bottom_right) and is_point_in_rectangle(thumb_tip_coords, top_left, bottom_right):
                    # Ajustar o volume com base na distância entre o polegar e o dedo indicador
                    distance = calculate_distance(thumb_tip, index_finger_tip)
                    volume_range = volume.GetVolumeRange()
                    min_vol = volume_range[0]
                    max_vol = volume_range[1]

                    # Normalizar a distância para o intervalo de volume
                    max_distance = 0.15  # Ajuste conforme necessário para a distância máxima
                    normalized_distance = min(1, distance / max_distance)
                    vol = min_vol + normalized_distance * (max_vol - min_vol)
                    volume.SetMasterVolumeLevel(vol, None)

                    # Exibir a linha entre o polegar e o indicador
                    cv2.line(frame, thumb_tip_coords, index_finger_tip_coords, (0, 255, 0), 2)

                    # Exibir a porcentagem de volume
                    volume_percentage = int((vol - min_vol) / (max_vol - min_vol) * 100)
                    cv2.putText(frame, f'Volume: {volume_percentage}%', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

    else:
        last_finger_x, last_finger_y = None, None  # Resetar a posição do dedo se nenhuma mão for detectada

    # Mostrando o frame
    cv2.imshow('Hand Tracking', frame)

    # Pressione 'q' para sair
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
