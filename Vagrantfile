Vagrant.configure("2") do |config|

  config.vm.define "debian_vm" do |debian|
    debian.vm.box = "generic/debian12"
    debian.vm.box_version  = "4.3.12"

    debian.vm.synced_folder "./challenges", "/tmp/remote_folder", type: "rsync", rsync__exclude: [".venv", ".idea", ".vscode", "__pycache__"]

    debian.vm.provision "file", source: "services/admin_simulator.service", destination: "/tmp/admin_simulator.service"
    debian.vm.provision "file", source: "services/file_browser.service", destination: "/tmp/file_browser.service"
    debian.vm.provision "file", source: "services/news_feed.service", destination: "/tmp/news_feed.service"

    debian.vm.provision "file", source: "setup/bash_history", destination: "/tmp/bash_history"

    debian.vm.provision "shell", path: "setup/provision.sh"
  end

  config.vm.define "kali_vm" do |kali|
    kali.vm.box = "kalilinux/rolling"
    kali.vm.box_version  = "2024.4"
  end

end