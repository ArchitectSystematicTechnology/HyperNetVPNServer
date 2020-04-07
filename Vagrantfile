
Vagrant.configure(2) do |config|
  config.vm.box = "debian/buster64"

  # Use the old insecure Vagrant SSH key for access.
  config.ssh.insert_key = false

  # Disable synchronization of the /vagrant folder for faster startup.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.provider :libvirt do |libvirt|
    libvirt.cpus = 1
    libvirt.memory = 3072
  end

  config.vm.define "floatrp1" do |m|
    m.vm.hostname = "floatrp1"
    m.vm.network "private_network", ip: "10.121.20.10", libvirt__dhcp_enabled: false
  end
  config.vm.define "floatapp1" do |m|
    m.vm.hostname = "floatapp1"
    m.vm.network "private_network", ip: "10.121.20.11", libvirt__dhcp_enabled: false
  end
end
