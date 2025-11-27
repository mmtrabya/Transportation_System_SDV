 # Transportation_System_SDV
# 🚗 A Modular Smart Transportation System Using Software-Defined Vehicles in Smart Cities  

<div align="center">

![GitHub repo size](https://img.shields.io/github/repo-size/mmtrabya/Transportation_System_SDV?color=brightgreen)
![GitHub contributors](https://img.shields.io/github/contributors/mmtrabya/Transportation_System_SDV)
![GitHub last commit](https://img.shields.io/github/last-commit/mmtrabya/Transportation_System_SDV?color=blue)
![GitHub stars](https://img.shields.io/github/stars/mmtrabya/Transportation_System_SDV?style=social)
![License](https://img.shields.io/badge/License-Apache-blue.svg)

</div>

---
## Repo Structure

```
├── atmega32
├── embedded_linux
├── esp32
├── LICENSE
├── models
├── raspberry_pi
├── README.md
├── scripts
├── sdv_application
├── sdv_firebase_key.json
├── server
└── tests
```
---

## 🌆 Project Overview  

**A Modular Smart Transportation System Using Software-Defined Vehicles (SDVs)** is an innovative approach to building a **connected, autonomous, and intelligent transportation ecosystem** for **smart cities**.  

This project integrates **AI, IoT, and automotive technologies** to design a scalable, modular, and secure platform that connects vehicles, infrastructure, and the cloud.  
By adopting a **Software-Defined Vehicle (SDV)** paradigm, the system enables **real-time decision making**, **secure over-the-air updates**, and **inter-vehicle communication**, supporting safer and smarter mobility for urban environments.  

---

🧩 Key Features

🚘 Software-Defined Vehicle (SDV) Architecture:
Modular design allows each vehicle subsystem to be managed and updated independently via software.

🧠 AI-Powered ADAS (Advanced Driver Assistance System):
Real-time lane detection, obstacle recognition, and decision-making using deep learning models built in Python and Jupyter Notebooks.

🌐 ESP-Based IoT Communication:
Efficient Vehicle-to-Vehicle (V2V) and Vehicle-to-Infrastructure (V2I) communication using ESP32 modules programmed in C/C++.

☁️ Modular FOTA/SOTA Update Mechanism:
Supports local Firmware Over-The-Air and Software Over-The-Air updates for ESP-based microcontrollers and onboard software.

🔐 Automotive Cybersecurity Layer:
Incorporates encryption and authentication mechanisms to ensure data integrity and prevent unauthorized access.

📊 Local Streamlit Dashboard:
Real-time visualization and monitoring of vehicle telemetry, AI model outputs, and system status.

📱 Flutter-Based Mobile Application:
A cross-platform mobile app developed with Flutter for residents of Smart Cities to book and manage Software-Defined Vehicles (SDVs), track availability, and monitor trip details.

---

## 🏗️ System Architecture  

```text
                 ┌─────────────────────────────┐
                 │       Smart City Cloud      │
                 │  (FOTA, AI, Data Analytics) │
                 └──────────────┬──────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────┴───────┐       ┌───────┴───────┐       ┌───────┴───────┐
│   SDV Vehicle 1│       │   SDV Vehicle 2│       │   SDV Vehicle 3│
│ ┌─────────────┐│       │ ┌─────────────┐│       │ ┌─────────────┐│
│ │   ESP32     ││       │ │   ESP32     ││       │ │   ESP32     ││
│ │   (V2X)     ││       │ │   (V2X)     ││       │ │   (V2X)     ││
│ └─────────────┘│       │ └─────────────┘│       │ └─────────────┘│
│ ┌─────────────┐│       │ ┌─────────────┐│       │ ┌─────────────┐│
│ │Raspberry Pi ││       │ │Raspberry Pi ││       │ │Raspberry Pi ││
│ │ (Edge AI)   ││       │ │ (Edge AI)   ││       │ │ (Edge AI)   ││
│ └─────────────┘│       │ └─────────────┘│       │ └─────────────┘│
│ ┌─────────────┐│       │ ┌─────────────┐│       │ ┌─────────────┐│
│ │ ATmega32    ││       │ │ ATmega32    ││       │ │ ATmega32    ││
│ │(Control)    ││       │ │(Control)    ││       │ │(Control)    ││
│ └─────────────┘│       │ └─────────────┘│       │ └─────────────┘│
└────────────────┘       └────────────────┘       └────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │ (V2V Communication via ESP32)
                 ┌──────────────┴──────────────┐
                 │   Mobile App Users          │
                 │  (Booking & Real-time       │
                 │   Tracking)                 │
                 └─────────────────────────────┘
```
---

| Category                       | Technologies                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Programming Languages**      | ![C](https://img.shields.io/badge/C-00599C?logo=c\&logoColor=white) ![C++](https://img.shields.io/badge/C++-00599C?logo=cplusplus\&logoColor=white) ![Python](https://img.shields.io/badge/Python-3670A0?logo=python\&logoColor=ffdd54) ![Dart](https://img.shields.io/badge/Dart-0175C2?logo=dart\&logoColor=white)                                                                                                                                                |
| **Development Environment**    | ![Jupyter](https://img.shields.io/badge/Jupyter-FA0F00?logo=jupyter\&logoColor=white) ![Flutter](https://img.shields.io/badge/Flutter-02569B?logo=flutter\&logoColor=white)                     ![Firebase](https://img.shields.io/badge/Firebase-DD2C00?logo=firebase\&logoColor=white)                                                                                                                                                                                                                                                           |
| **AI & ML Frameworks**         | ![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch\&logoColor=white) ![OpenCV](https://img.shields.io/badge/OpenCV-27338e?logo=opencv\&logoColor=white) ![YOLO](https://img.shields.io/badge/YOLO-00FFFF?logo=yolo\&logoColor=black)                                                                                                                                                                                                               |
| **Embedded Systems & IoT**     | ![ESP32](https://img.shields.io/badge/ESP32-000000?logo=espressif\&logoColor=white) ![ATmega32A](https://img.shields.io/badge/ATmega32A-00205B?logo=atmel\&logoColor=white) ![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?logo=raspberrypi\&logoColor=white)                                                                                                                                                                                   |
| **Visualization & Monitoring** | ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit\&logoColor=white)                                                                                                                                                                                                                                                                                                                                                                         |
| **Version Control**            | ![Git](https://img.shields.io/badge/Git-F05032?logo=git\&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-181717?logo=github\&logoColor=white)                                                                                                                                                                                                                                                                                                        |
| **Mobile App Development**     | ![Flutter](https://img.shields.io/badge/Flutter-02569B?logo=flutter\&logoColor=white) ![Dart](https://img.shields.io/badge/Dart-0175C2?logo=dart\&logoColor=white) ![LottieFiles](https://img.shields.io/badge/LottieFiles-00D9A3?logo=lottie\&logoColor=white) ![SplashScreen](https://img.shields.io/badge/Splash%20Screen-FFD700?logo=flutter\&logoColor=black)                                                                                                  |
| **Supported Platforms**        | ![Android](https://img.shields.io/badge/Android-3DDC84?logo=android\&logoColor=white) ![iOS](https://img.shields.io/badge/iOS-000000?logo=apple\&logoColor=white) ![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows\&logoColor=white) ![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux\&logoColor=black) ![macOS](https://img.shields.io/badge/macOS-000000?logo=apple\&logoColor=white) ![Web](https://img.shields.io/badge/Web-42) |



---

## 💡 Project Modules  

- 🚘 **ADAS (Advanced Driver Assistance System)**  
  - Implements **object detection**, **lane detection**, and **environmental awareness** using deep learning.  
  - Built using **Python**, **OpenCV**, **PyTorch**, and **YOLO** in **Jupyter Notebooks** for training and testing.  
  - Provides **perception data** to the ESP microcontrollers for real-time decision support.  

- 🌐 **IoT Communication (V2X) Module**  
  - Developed using **ESP32** boards programmed in **C/C++**.  
  - Facilitates communication between multiple SDVs using wireless protocols such as **Wi-Fi** and **ESP-NOW**.  
  - Enables **Vehicle-to-Vehicle (V2V)** and **Vehicle-to-Infrastructure (V2I)** data exchange.  

- ☁️ **FOTA/SOTA Module**  
  - Supports **Firmware Over-The-Air (FOTA)** and **Software Over-The-Air (SOTA)** updates.  
  - Designed for **modular updates** without halting the entire system.  
  - Ensures system scalability and maintainability.  

- 🔐 **Automotive Cybersecurity Module**  
  - Implements **lightweight encryption algorithms** to secure communication between vehicles.  
  - Includes **intrusion detection mechanisms** to monitor irregular data transmission behavior.  
  - Focuses on ensuring **data integrity and protection** across all system modules.  

- 📊 **Streamlit Dashboard**  
  - Provides **real-time visualization** of system data, AI model outputs, and operational metrics.  
  - Displays important indicators such as **speed**, **distance**, **detection confidence**, and **system health**.  
  - Runs **locally** — no internet, cloud, or database dependency.  
  - Serves as a **monitoring and analysis tool** for debugging and demonstration.  
- 📱 Mobile App Development
  - Developed using Flutter and Dart for cross-platform deployment (Android, iOS, Web, Windows, Linux, macOS).
  - Designed for residents of Smart Cities to book, manage, and monitor Software-Defined Vehicles (SDVs).
  - Features interactive UI with Lottie animations and a custom splash screen for a seamless user experience.
  - Integrates with backend APIs for SDV availability, status tracking, and trip history visualization.

---

© 2025 Mohammed Tarabay — Developed as part of the Smart Transportation System (SDV) Project. All rights reserved.
