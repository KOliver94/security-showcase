useradd -m -s /bin/bash frank
echo 'frank:$6$/pNKDKkSOlW2cUo2$iqXyyyL69Yc.HykOLBlEiTd16MvertveLs/LP3g943pFYMt5yf54JGcdNcxN8msmJRXxwt.ZFAhmLPIApCqkz.' | chpasswd --encrypted
usermod -aG sudo frank

useradd -m -s /bin/bash bob
echo 'bob:$6$7uRqC492Ms.aLUoM$w7Ib46srUCKmQhgCavdcEQ8Nmhm6MPPYVgs1DKR4y5dh3S3haQ1IpfZxApHm7RLS8qtoKL.PfJzMwgLJN.72F1' | chpasswd --encrypted

mkdir -p /var/www
cp -r /tmp/remote_folder/* /var/www
chown -R bob:bob /var/www
find /var/www -type d -exec chmod 750 {} \;
find /var/www -type f -exec chmod 640 {} \;

apt update
apt install -y python3 python3-venv python3-pip

for APP in "news-feed" "file-browser" "news-feed/helpers"; do
  APP_DIR="/var/www/$APP"

  if [ ! -d "$APP_DIR/.venv" ]; then
    python3 -m venv $APP_DIR/.venv
  fi

  source $APP_DIR/.venv/bin/activate
  pip install --upgrade pip -r $APP_DIR/requirements.txt

  if [ "$APP" == "file-browser" ]; then
    cd $APP_DIR || exit
    flask init-db
    flask generate-files
    chown bob:bob file-browser.db
  elif [ "$APP" == "news-feed" ]; then
    cd $APP_DIR || exit
    flask init-db
    chown bob:bob news-feed.db
  elif [ "$APP" == "news-feed/helpers" ]; then
    cd $APP_DIR || exit
    playwright install --with-deps chromium-headless-shell
  fi
done

mv /tmp/admin_simulator.service /etc/systemd/system/admin_simulator.service
mv /tmp/file_browser.service /etc/systemd/system/file_browser.service
mv /tmp/news_feed.service /etc/systemd/system/news_feed.service

systemctl daemon-reload
systemctl enable admin_simulator
systemctl enable file_browser
systemctl enable news_feed
systemctl start admin_simulator
systemctl start file_browser
systemctl start news_feed

mv /tmp/bash_history /home/bob/.bash_history
chown bob:bob /home/bob/.bash_history
chmod 600 /home/bob/.bash_history