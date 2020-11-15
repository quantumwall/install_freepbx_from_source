#!/usr/bin/env python3

import subprocess, argparse

parser = argparse.ArgumentParser()
parser.add_argument('-v')
args = parser.parse_args()
centos_version = args.v

# centos_version = subprocess.run("grep VERSION_ID /etc/*release | cut -d '=' -f2 | tr -d '\"\"'",
#                               shell=True, stdout=subprocess.PIPE, encoding='utf-8')
# centos_version = centos_version.stdout.rstrip()
MariaDB_repo_file = '''# MariaDB 10.5 CentOS repository list - created 2020-07-22 13:27 UTC
# http://downloads.mariadb.org/mariadb/repositories/
[mariadb]
name = MariaDB
baseurl = http://yum.mariadb.org/10.5/centos7-amd64
gpgkey=https://yum.mariadb.org/RPM-GPG-KEY-MariaDB
gpgcheck=1'''
asterisk_url_source = 'http://downloads.asterisk.org/pub/telephony/asterisk/asterisk-16-current.tar.gz'
freepbx_url_source = 'http://mirror.freepbx.org/modules/packages/freepbx/freepbx-15.0-latest.tgz'
jansson_url_source = 'https://github.com/akheron/jansson.git'
pjsip_url_source = 'https://github.com/pjsip/pjproject.git'
base_compilation_folder = '/usr/local/src'

def Print(text):
    print('{:~^80}'.format(text))

def install_pbx(os_version):
    try:
        if os_version == '7':
            pm = 'yum'
        else:
            pm = 'dnf'
        Print('Disabling selinux')
        subprocess.run("sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/sysconfig/selinux && setenforce 0", shell=True)
        print()
        Print('Connecting epel repo')
        subprocess.run(f'{pm} -y install epel-release', shell=True)
        Print('Updating OS')
        subprocess.run(f'{pm} -y update && {pm} -y groupinstall core base "Development Tools"', shell=True)
        if os_version == '7':
            Print('Generate repo file for MariaDB')
            with open('/etc/yum.repos.d/MariaDB.repo', 'w') as repo_file:
                repo_file.write(MariaDB_repo_file)
            Print('Installing MariaDB')
            subprocess.run(f'{pm} -y install MariaDB-server MariaDB-client MariaDB-shared', shell=True)
        else:
            Print('Installing dependences')
            subprocess.run(f'{pm} -y install tftp-server ncurses-devel sendmail sendmail-cf newt-devel'
                           f' libxml2-devel libtiff-devel gtk2-devel subversion kernel-devel git crontabs'
                           f' cronie cronie-anacron wget sqlite-devel net-tools gnutls-devel'
                           f' unixODBC sox lame', shell=True)
            Print('Installing MariaDB')
            subprocess.run(f'{pm} -y module install mariadb', shell=True)
        Print('Put mariadb in autostart')
        subprocess.run('systemctl start mariadb && systemctl enable mariadb', shell=True)
        Print('Permit http and https ports on firewalld')
        subprocess.run("firewall-cmd --add-service={http,https} --permanent && firewall-cmd --reload", shell=True)

        if os_version == '7':
            Print('Connecting remi repo')
            subprocess.run('rpm -Uhv http://rpms.remirepo.net/enterprise/remi-release-7.rpm', shell=True)
            Print('Installing yum-utils')
            subprocess.run('yum install yum-utils', shell=True)
            Print('Activating remi repo for php7.2')
            subprocess.run('yum-config-manager --enable remi-php72', shell=True)
            Print('Installing php packages')
            subprocess.run(f'{pm} -y install wget php php-pear php-cgi php-common php-curl php-mbstring php-gd'
                           f' php-mysql php-gettext php-bcmath php-zip php-xml php-imap php-json php-process'
                           f' php-snmp lame sox', shell=True)
            Print('Installing php packages')
            subprocess.run(f'{pm} -y install httpd', shell=True)
            subprocess.run(r"sed -i 's/^\(User\|Group\).*/\1 asterisk/' /etc/httpd/conf/httpd.conf", shell=True)
            subprocess.run("sed -i 's/AllowOverride None/AllowOverride All/' /etc/httpd/conf/httpd.conf", shell=True)
            subprocess.run(r"sed -i 's/\(^upload_max_filesize = \).*/\1120M/' /etc/php.ini", shell=True)
            Print('Installing nodejs')
            subprocess.run("curl -sL https://rpm.nodesource.com/setup_10.x | bash -", shell=True)
            subprocess.run(f"{pm} clean all && sudo yum makecache fast", shell=True)
            subprocess.run(f"{pm} -y install gcc-c++ make nodejs", shell=True)
        else:
            Print('Installing web-server')
            subprocess.run(f"{pm} -y install @httpd", shell=True)
            subprocess.run("rm -f /var/www/html/index.html", shell=True)
            Print('Enabling web-server')
            subprocess.run("systemctl enable --now httpd", shell=True)
            Print('Installing php packages')
            subprocess.run(f'{pm} -y install wget @php php-pear php-cgi php-common php-curl php-mbstring '
                           f'php-gd php-mysqlnd php-gettext php-bcmath php-zip php-xml php-json php-process php-snmp',
                           shell=True)
            subprocess.run(r"sed -i 's/\(^upload_max_filesize = \).*/\1120M/' /etc/php.ini", shell=True)
            subprocess.run(r"sed -i 's/\(^memory_limit = \).*/\1512M/' /etc/php.ini", shell=True)
            subprocess.run(r"sed -i 's/^\(User\|Group\).*/\1 asterisk/' /etc/httpd/conf/httpd.conf", shell=True)
            subprocess.run("sed -i 's/AllowOverride None/AllowOverride All/' /etc/httpd/conf/httpd.conf", shell=True)
            subprocess.run(r"sed -i 's/^\(user\|group\).*/\1 = asterisk/' /etc/php-fpm.d/www.conf", shell=True)
            subprocess.run(r"sed -i 's/^\(listen.acl_users\).*/\1 = asterisk/' /etc/php-fpm.d/www.conf", shell=True)
            Print('Restarting httpd and php-fpm')
            subprocess.run("systemctl enable --now php-fpm httpd && systemctl restart php-fpm httpd", shell=True)
            Print('Installing nodejs')
            subprocess.run(f"{pm} -y module install nodejs:10", shell=True)
            Print('Installing jansson and pjsip')
            subprocess.run(f"cd {base_compilation_folder} && git clone https://github.com/akheron/jansson.git && "
                           "cd jansson && autoreconf -i && ./configure --prefix=/usr/ && make && make install", shell=True)
            subprocess.run(f'cd {base_compilation_folder} && git clone https://github.com/pjsip/pjproject.git && '
                           f'cd pjproject && ./configure CFLAGS="-DNDEBUG -DPJ_HAS_IPV6=1" --prefix=/usr '
                           f'--libdir=/usr/lib64 --enable-shared --disable-video --disable-sound --disable-opencore-amr && '
                           f'make dep && make && make install && ldconfig', shell=True)
            subprocess.run(f"{pm} config-manager --set-enabled PowerTools && {pm} -y install libedit-devel", shell=True)
        Print(f'Download Asterisk and FreePBX en {base_compilation_folder}')
        subprocess.run(f"cd {base_compilation_folder} && wget {asterisk_url_source} {freepbx_url_source} && "
                       f"tar xvf asterisk-16-current.tar.gz &&"
                       f"tar xvf freepbx-15.0-latest.tgz && rm -f asterisk-16-current.tar.gz && "
                       f"rm -f freepbx-15.0-latest.tgz", shell=True)
        source_folders = subprocess.run(f"ls {base_compilation_folder} | grep 'asterisk\|freepbx'", shell=True,
                                        stdout=subprocess.PIPE, encoding='utf-8')
        asterisk_folder, freepbx_folder = source_folders.stdout.split()
        Print('Compilation of Asterisk')
        subprocess.run(f"cd {base_compilation_folder}/{asterisk_folder} && contrib/scripts/install_prereq install && "
                       f"contrib/scripts/get_mp3_source.sh", shell=True)
        if os_version == '7':
            subprocess.run(f"cd {base_compilation_folder}/{asterisk_folder} &&"
                           f" ./configure --with-pjproject-bundled --with-jansson-bundled --with-crypto "
                           f"--with-ssl=ssl --with-srtp", shell=True)
        else:
            subprocess.run(f"cd {base_compilation_folder}/{asterisk_folder} && ./configure --libdir=/usr/lib64", shell=True)
        subprocess.run(f"cd {base_compilation_folder}/{asterisk_folder} && make menuselect && "
                       f"make && make install && make config && make samples && ldconfig", shell=True)
        Print('Сreating an Asterisk user and assigning permissions to directories')
        if os_version == '7':
            subprocess.run('sed -i \'s/ASTARGS=""/ASTARGS="-U asterisk"/g\' /usr/sbin/safe_asterisk', shell=True)
            subprocess.run("useradd -m asterisk", shell=True)
            subprocess.run("chown asterisk.asterisk /var/run/asterisk", shell=True)
            subprocess.run("chown -R asterisk.asterisk /etc/asterisk /var/{lib,log,spool}/asterisk "
                           "/usr/lib/asterisk", shell=True)
        else:
            subprocess.run("groupadd asterisk", shell=True)
            subprocess.run("useradd -r -d /var/lib/asterisk -g asterisk asterisk", shell=True)
            subprocess.run("usermod -aG audio,dialout asterisk", shell=True)
            subprocess.run("chown -R asterisk.asterisk /etc/asterisk /var/{lib,log,spool}/asterisk "
                           "/usr/lib64/asterisk", shell=True)
            subprocess.run('sed -i \'s/#AST/AST/\' /etc/sysconfig/asterisk', shell=True)
            subprocess.run('sed -i "s/;runuser/runuser/" /etc/asterisk/asterisk.conf', shell=True)
            subprocess.run('sed -i "s/;rungroup/rungroup/" /etc/asterisk/asterisk.conf', shell=True)
        subprocess.run('sed -i \'s";\[radius\]"\[radius\]"g\' /etc/asterisk/cdr.conf', shell=True)
        subprocess.run('sed -i \'s";radiuscfg => /usr/local/etc/radiusclient-ng/radiusclient.conf"radiuscfg => '
                       '/etc/radcli/radiusclient.conf"g\' /etc/asterisk/cel.conf', shell=True)
        subprocess.run('sed -i \'s";radiuscfg => /usr/local/etc/radiusclient-ng/radiusclient.conf"radiuscfg => '
                       '/etc/radcli/radiusclient.conf"g\' /etc/asterisk/cdr.conf', shell=True)
        Print('Start and put Asterisk in autostart')
        subprocess.run('systemctl restart asterisk && systemctl enable asterisk', shell=True)
        Print('Compilation of FrePBX')
        subprocess.run(f"cd {base_compilation_folder}/{freepbx_folder} && ./start_asterisk start && ./install -n",
                       shell=True)
        if os_version == '7':
            Print('Starting web server')
            subprocess.run('systemctl start httpd && systemctl enable httpd', shell=True)
        else:
            Print('Restarting web server')
            subprocess.run('systemctl restart httpd', shell=True)
        Print('DONE')
        return 0
    except KeyboardInterrupt:
        print("Installation was interrupted by the user")
        exit(1)

install_pbx(centos_version)
