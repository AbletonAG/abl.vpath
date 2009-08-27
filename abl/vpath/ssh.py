import paramiko

#----------------------------------------------------------------------------

class IgnoreMissingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """
    IgnoreMissingHostKeyPolicy is used by SSHRemoteActions in order to
    ignore a missing host_key file. Since we are only locally active, we
    don't really care if we are talking to the right server :-)
    """

    def missing_host_key(self, client, hostname, key):
        pass


@decorator
def ssh_retry(func, self, *args, **argd):
    """
    simple ssh retry decorator to try a one shot retry in case there
    is a ChannelException.
    """
    try:
        return func(self, *args, **argd)
    except paramiko.ChannelException:
        try:
            self.close()
        except:pass
        self._initialize()
        return func(self, *args, **argd)

class SshFileSystem(FileSystem):

    def _initialize(self):
        self.client = client = paramiko.SSHClient()
        client.set_missing_host_key_policy(IgnoreMissingHostKeyPolicy())
        client.connect(
            self.hostname,
            username = self.username,
            timeout=5.0,
            **self.extras
            )
        self.sftp_client = client.open_sftp()

    def close(self):
        self.sftp_client.close()
        self.client.close()

    def open(self, unc, options=None):
        if options is not None:
            return closing(self.sftp_client.open(self._path(unc), options))
        else:
            return closing(self.sftp_client.open(self._path(unc)))

    @ssh_retry
    def listdir(self, unc, options=None):
        return self.sftp_client.listdir(self._path(unc))

    @ssh_retry
    def removefile(self, unc):
        return self.sftp_client.remove(self._path(unc))

    @ssh_retry
    def removedir(self, unc):
        return self.sftp_client.rmdir(self._path(unc))

    @ssh_retry
    def mkdir(self, unc):
        return self.sftp_client.mkdir(self._path(unc))

    @ssh_retry
    def exists(self, unc):
        try:
            self.sftp_client.stat(self._path(unc))
            return True
        except IOError:
            return False

    def isfile(self, unc):
        return self.exists(unc) and not self.isdir(unc)

    @ssh_retry
    def isdir(self, unc):
        try:
            status = self.sftp_client.stat(self._path(unc))
            return S_ISDIR(status.st_mode)
        except IOError:
            return False

    @ssh_retry
    def copy(self, source, dest, options=None, ignore=None):
        if source.scheme == 'ssh' and dest.scheme == 'file' and options is None:
            self.sftp_client.get(source.path, dest.path)
        elif (
            source.scheme == 'file' and
            dest.scheme == 'ssh' and
            options is None
            ):
            self.sftp_client.put(source.path, dest.path)
        else:
            super(SshFileSystem, self).copy(source, dest, options, ignore)

