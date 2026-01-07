"""
Simple desktop UI for ATCC processing using PySimpleGUI.
Allows users to select a full-day video, choose interval, model, and run the
pipeline. Displays progress logs and links to outputs.
"""
from __future__ import annotations

import os
from pathlib import Path
import PySimpleGUI as sg

from atcc_pipeline import main as pipeline_main


def run_pipeline(values):
    # Build argv for atcc_pipeline.main
    argv = [
        "--video", values["-VIDEO-"],
        "--outdir", values["-OUT-"],
        "--interval-mins", str(values["-INTERVAL-"]),
        "--model", values["-MODEL-"],
        "--base-start", values["-BASE-"],
        "--line", values["-LINE-"],
        "--morning", values["-MORNING-"],
        "--evening", values["-EVENING-"],
    ]
    if values.get("-CLASSMAP-"):
        argv.extend(["--class-map", values["-CLASSMAP-"]])

    pipeline_main(argv)


def main():
    sg.theme("LightBlue2")

    layout = [
        [sg.Text("ATCC Desktop Processor", font=("Arial", 16, "bold"))],
        [sg.Text("Full-day video"), sg.Input(key="-VIDEO-"), sg.FileBrowse(file_types=(("Video Files", "*.mp4;*.avi;*.mov"),))],
        [sg.Text("Output folder"), sg.Input(default_text=str(Path.cwd()/"atcc_output"), key="-OUT-"), sg.FolderBrowse()],
        [
            sg.Text("Interval (min)"), sg.Combo([15, 30], default_value=15, key="-INTERVAL-", size=(6,1)),
            sg.Text("Model"), sg.Input(default_text="yolov8n.pt", key="-MODEL-", size=(20,1)), sg.FileBrowse(file_types=(("YOLO models", "*.pt;*.onnx"),))
        ],
        [
            sg.Text("Base start HH:MM"), sg.Input("00:00", key="-BASE-", size=(8,1)),
            sg.Text("Line x,y;x,y (norm)"), sg.Input("0,0.5;1,0.5", key="-LINE-", size=(16,1)),
            sg.Text("Morning"), sg.Input("6-12", key="-MORNING-", size=(6,1)),
            sg.Text("Evening"), sg.Input("16-21", key="-EVENING-", size=(6,1)),
        ],
        [sg.Text("Class map (JSON)"), sg.Input(key="-CLASSMAP-"), sg.FileBrowse(file_types=(("JSON", "*.json"),))],
        [sg.HorizontalSeparator()],
        [sg.Button("Run"), sg.Button("Exit")],
        [sg.Multiline(size=(100,20), key="-LOG-", autoscroll=True, reroute_stdout=True, reroute_stderr=True, write_only=True)],
    ]

    window = sg.Window("ATCC Desktop", layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event == "Run":
            try:
                run_pipeline(values)
                sg.popup("Processing completed.")
            except Exception as e:
                sg.popup_error(f"Error: {e}")

    window.close()


if __name__ == "__main__":
    main()
