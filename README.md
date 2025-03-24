# atlas
A script to convert strava activities to a series of pyplot images.

## requirements
- python
- poetry
- ffpmeg

## data
The source data will be the exported data from strava (see: https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export).
The file should have a structure as follows:
```
export_<some_id>
- activities/
- activities.csv
```

## run  

**initialize env**  
`poetry install`
  
**run python script to generate images**
You can get your originating latitude and longitude by right-clicking on google maps  
`python plot_gps_parallel.py <strava export dir> <latitude> <longitude> <radius> <starting date> <steps>`


  
**run ffmpeg to generate an mp4 video**  
`ffmpeg -f image2 -framerate 30 -i images/%04d-export.png  -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -movflags +faststart output.mp4`  