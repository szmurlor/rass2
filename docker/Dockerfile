# Docker file for a slim Ubuntu-based Python3 image

FROM ubuntu:bionic

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev wget unzip unrar gcc make openssl ca-certificates apt-transport-https git iputils-ping iproute2 \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

RUN pip3 install flask \
  flask-sqlalchemy \
  uwsgi \
  pydicom

RUN git clone https://goope.ee.pw.edu.pl/goope/rass2-flask.git \
  && cd rass2-flask 

RUN apt-get install -y iproute2

EXPOSE 5000 

WORKDIR /rass2-flask
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

CMD ["bash"]
#CMD ["sh", "-c", "ip a|grep inet; python3 rass.py"]
#ENTRYPOINT ["bash"]
