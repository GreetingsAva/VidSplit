from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
import numpy as np
import os
from scipy import stats
import sys

def calculate_average_loudness(audio, chunk_size=1000, is_fullvideo=False):
    # Initialize RMS and sample count
    rms_total = 0
    count = 0

    # Initialize list to store dBFS values
    dbfs_values = []

    # Iterate over the audio data in chunks
    for i in range(0, len(audio), chunk_size):
        # Extract the current chunk
        chunk = audio[i:i+chunk_size]

        # Calculate the RMS (Root Mean Square) of the current chunk
        samples = np.array(chunk.get_array_of_samples())
        rms = np.sqrt(np.mean(samples**2))

        # Convert RMS to dBFS (decibels full scale)
        dbfs = 20 * np.log10(rms)

        # Add dBFS value to the list
        dbfs_values.append(dbfs)

        # Update the total RMS and sample count
        rms_total += rms * len(samples)
        count += len(samples)

    # Calculate the overall RMS
    rms = rms_total / count

    # Convert RMS to dBFS (decibels full scale)
    average_dbfs = 20 * np.log10(rms)

    # Calculate the average peak dBFS
    average_peak_dbfs = np.mean([dbfs for dbfs in dbfs_values if dbfs > average_dbfs])

    # Calculate the difference between the average peak dBFS and the average dBFS
    dbfs_diff = average_peak_dbfs - average_dbfs

    # Set max_db to a percentage above the average dBFS
    threshold_db = average_dbfs  # Adjust the percentage as needed

    return average_dbfs


def split_video_by_audio(input_video_path, output_folder, min_increase_duration=30, analysis_window=10):
    # Load the video clip
    video_clip = VideoFileClip(input_video_path)

    # Write the audio to a wav file
    video_clip.audio.write_audiofile("temp.wav")

    # Load the wav file as an AudioSegment object
    audio = AudioSegment.from_wav("temp.wav")

    # Calculate the average loudness +2% and set it as the threshold
    threshold_db = 20

    # Get the duration of the video in seconds
    video_duration = video_clip.duration

    # Initialize start and end time for the current segment
    start_time = 0
    end_time = analysis_window

    # Flag to indicate whether we are currently in an increased volume segment
    in_increased_volume_segment = False

    print("Starting audio analysis...")  # Debug print

    # Iterate through the audio data in a sliding window
    while end_time < video_duration:
        print(f"Analyzing audio from {start_time} to {end_time} seconds...")  # Debug print

        # Extract audio segment for analysis
        current_audio_segment = audio[int(start_time*1000):int(end_time*1000)]

        # Check if the audio segment is empty
        if len(current_audio_segment) == 0:
            start_time = end_time
            end_time += analysis_window
            continue

        # Calculate the average loudness of the current segment
        current_dBFS = calculate_average_loudness(current_audio_segment)

        print(f"Current dBFS: {current_dBFS}, Threshold dBFS: {threshold_db}")  # Debug print

        # Check if the average loudness exceeds the threshold
        if current_dBFS > threshold_db:
            # If not already in an increased volume segment, start a new one
            if not in_increased_volume_segment:
                in_increased_volume_segment = True
                segment_start_time = start_time  # Start of the loud segment
        else:
            # If in an increased volume segment, check if it has been a minute since the loudness dropped
            if in_increased_volume_segment and end_time - segment_start_time >= min_increase_duration:
                # Check if the last min_increase_duration seconds are below the threshold
                last_sec_audio = audio[int((end_time-analysis_window)*1000):int(end_time*1000)]
                last_sec_dBFS = calculate_average_loudness(last_sec_audio)
                if last_sec_dBFS <= threshold_db:
                    in_increased_volume_segment = False
                    segment_end_time = end_time  # End of the loud segment
                    subclip = video_clip.subclip(segment_start_time, segment_end_time)
                    output_filename = f"{output_folder}/segment_{segment_start_time}_{segment_end_time}.mp4"
                    subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac", verbose=False)

        # Move to the next sliding window
        start_time = end_time
        end_time += analysis_window  # Adjust the window size as needed

    if in_increased_volume_segment:
        # End of the loud segment is the end of the video
        segment_end_time = video_duration
        subclip = video_clip.subclip(segment_start_time, segment_end_time)
        output_filename = f"{output_folder}/segment_{segment_start_time}_{segment_end_time}.mp4"
        subclip.write_videofile(output_filename, codec="libx264", audio_codec="aac", verbose=False)

    print("Audio analysis completed.")  # Debug print

    # Close the video clip
    video_clip.close()

    # Remove the temporary wav file
    os.remove("temp.wav")



# Example usage
input_video_path = "F:/AJ/Python Splitting/Split/split.mkv"
output_folder = "F:/AJ/Python Splitting/Complete/"
split_video_by_audio(input_video_path, output_folder)
