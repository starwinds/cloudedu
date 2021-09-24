FROM jupyter/datascience-notebook:latest
USER root
RUN apt-get -y install git
RUN cd /home/jovyan/ && git clone https://github.com/starwinds/ktcloud-toolkit
