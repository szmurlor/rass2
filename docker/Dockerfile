# Docker file for a slim Ubuntu-based Python3 image

FROM ubuntu:bionic

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
     wget unzip unrar gcc make openssl ca-certificates \
     apt-transport-https \
     git iputils-ping iproute2 redis \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

RUN pip3 install flask \
  flask-sqlalchemy \
  uwsgi \
  pydicom \
  redis \
  rq \
  Flask-Babel \
  markdown \
  dash

RUN git clone https://github.com/szmurlor/rass2.git \
  && cd rass2 

RUN pip3 install numpy
RUN pip3 install scipy
RUN pip3 install pandas

EXPOSE 5000 

WORKDIR /rass2
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

CMD ["bash"]
#CMD ["sh", "-c", "ip a|grep inet; python3 rass.py"]
#ENTRYPOINT ["bash"]
