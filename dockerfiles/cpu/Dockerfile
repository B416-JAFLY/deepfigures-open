# image for running DeepFigures

FROM tensorflow/tensorflow:1.15.5

ENV LC_ALL C.UTF-8
ENV TZ=Asia/Shanghai
# install system packages
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN sed -i 's/http:\/\/archive.ubuntu.com/http:\/\/mirrors.tuna.tsinghua.edu.cn\/ubuntu/g' /etc/apt/sources.list
RUN apt-get clean && apt-get update --fix-missing && apt-get install -y git curl gcc build-essential tcl g++ zlib1g-dev libjpeg8-dev libtiff5-dev libpng-dev tcl-dev tk-dev python3 python3-pip python3-tk ghostscript poppler-utils
RUN apt-get install -y openjdk-8-jre
RUN apt-get install -y texlive-latex-base
RUN apt-get install -y texlive-fonts-recommended
RUN mkdir -p /tmp/packages
ADD ./software/texlive-fonts-extra.deb /tmp/packages
RUN dpkg -i /tmp/packages/texlive-fonts-extra.deb
RUN apt-get    install  -y      texlive-fonts-extra
RUN apt-get    install  -y      texlive-latex-extra 
RUN apt-get install -y software-properties-common 
RUN add-apt-repository 'deb http://security.ubuntu.com/ubuntu xenial-security main' 
RUN apt update 
RUN apt install libjasper1 libjasper-dev 
WORKDIR /work

# install python packages

ADD ./requirements_lite.txt /work

RUN pip3 install --upgrade pip \
 && pip install Cython==0.25.2
# RUN pip3 install -r ./requirements_lite.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
RUN pip3 install --upgrade pip && pip install --prefer-binary -r ./requirements_lite.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

ADD ./vendor/tensorboxresnet /work/vendor/tensorboxresnet
RUN pip3 install -e /work/vendor/tensorboxresnet -i https://pypi.tuna.tsinghua.edu.cn/simple/

ADD . /work
RUN pip3 install --quiet -e /work

CMD [ "/bin/bash" ]