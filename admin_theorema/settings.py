CAMDIR = '/home/_processInstances'
CONFIG_NAME = 'theorem.conf'
QUAD_CONFIG_NAME = 'config.json'
DBDIR = 'DB'
COMMAND = '/usr/bin/processInstance'
COMMAND_QUAD = '/usr/bin/kvadrator %s' % QUAD_CONFIG_NAME
ADDITIONAL_CONFIG = 'conf.conf'
LAG = 2
SUPERVISOR_CAMERAS_CONF = '/etc/supervisor/conf.d/cameras.conf'

TEMPLATE = """[General]
Port={port}

[AnalysisParams]
Diff%20Threshold=18
Bg%20threshold=15
Fg%20Threshold=50
Motion%20Threshold=0.2
Total%20Threshold=0.08
Downscale%20Coeff={downscale_coeff}
Experimental=false
Valid%20motion%20bin%20height=8
Use%20virtual%20date=false
DebugImageIndex=0
Debug%20objects=false
Produce%20Debug=false

Motion%20based%20analysis={motion_analysis}
Difference%20based%20analysis={diff_analysis}

[PipelineParams]

Pipeline%20Name=cam{id}
Camera%20name={name}
Input%20Stream%20Url={address}
Output%20Url=ws://localhost:{output_port}
Source%20Output%20Url=rtmp://localhost:1935/vasrc/cam{id}

Archive%20Path={archive_path}
Database%20Path=video_analytics
Output%20Stream%20Bitrate={compress_level}

Global%20Scale={global_scale}
fps={fps}
statisticPeriodDays=14
Processing%20Interval%20Sec=600
Statistic%20Interval%20Sec=600


Server%20address=127.0.0.1
Notification%20smtp%20address=
Notification%20smtp%20login=
Notification%20smtp%20password=
Notification%20start%20time=00:00:00
Notification%20syserr%20email=
storage_life={storage_life}
indefinitely={indefinitely} """


