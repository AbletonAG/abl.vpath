import pysvn

class SvnFileSystem(FileSystem):

    def _initialize(self):
        def svn_login_callback(realm, username, may_save):
            username = self.username
            password = self.password
            return True, username, password, True

        self.lock = threading.Lock()
        self.client = pysvn.Client()
        self.client.callback_get_login = svn_login_callback
        rn = self.extras.get('revision_number', 0)
        self.revision_number = None
        if rn:
            self.revision_number = pysvn.Revision(
                pysvn.opt_revision_kind.number,
                rn
                )

    def _checkout_or_update(self, source, dest):
        LOGGER.info('SvnFileSystem._checkout_or_update')
        LOGGER.info('SRC: %s' % source)
        LOGGER.info('DEST: %s' % dest)
        do_checkout = True
        if dest.isdir():
            LOGGER.info('try an update')
            try:
                with self.lock:
                    if self.revision_number:
                        self.client.update(
                            dest.path,
                            revision=self.revision_number
                            )
                    else:
                        self.client.update(dest.path)
                    for file_status in self.client.status(
                        dest.path,
                        recurse=True,
                        get_all=False
                        ):
                        if not file_status['is_versioned']:
                            pth = URI(file_status['path'])
                            LOGGER.debug('removing %s' % pth.path)
                            if pth.isfile():
                                pth.remove()
                            elif pth.isdir():
                                pth.remove('r')
                    do_checkout = False

            except:
                do_checkout = False
                print "================================="
                traceback.print_exc()
                print "================================="
                if dest.isdir():
                    dest.remove('r')

        if do_checkout:
            LOGGER.info('try an checkout')
            base_dir = dest.directory()
            if not base_dir.isdir():
                base_dir.makedirs()
            with self.lock:
                if self.revision_number is not None:
                    self.client.checkout(
                        source.uri,
                        dest.path,
                        revision=self.revision_number
                        )
                else:
                    self.client.checkout(source.uri, dest.path)

    def listdir(self, source, options=None):
        if not source.scheme == 'svn':
            raise WrongSchemeError("svn copy needs a svn url as first arg")
        if not source.isdir():
            raise PathError("%s must be a directory" % source.uri)
        if options == 'r':
            with self.lock:
                result = self.client.list(source.uri, recurse=True)
            result = [x[0].repos_path for x in result]
            orig = result[0]
            result = result[1:]
            rlen = len(orig) + 1
            return [x[rlen:] for x in result]
        else:
            with self.lock:
                result = self.client.list(source.uri, depth=pysvn.depth.immediates)
            # call will return info about itself as well :-(
            result = result[1:]
            result = [x[0].repos_path for x in result]
            return [x.rsplit('/',1)[1] for x in result]

    def copy(self, source, dest, options=None, **argd):
        """
        copy:  do an 'svn checkout' or 'svn update', depending on the
               existance of dest.

        TODO: think about 'svnlocal' scheme for doing operations on
              an already checked out repository. Depending on (source, dest)
              combinations, the following operations could be possible:
              (svn, file): svn export
              (svn, svn): svn cp
              (svn, svnlocal): svn co / svn update
              (svnlocal, svn): svn ci
              (svnlocal, svnlocal): merge
        """
        if not source.scheme == 'svn':
            raise WrongSchemeError("svn copy needs a svn url as first arg")
        if not dest.scheme == 'file':
            raise WrongSchemeError("svn copy needs a file url as second arg")
        if 'r' in options: # we are doing a checkout or update
            self._checkout_or_update(source, dest)
        else:
            raise OptionsError("svn copy needs the 'r' option for now")

    def move(self, source, destination):
        raise NoDefinedOperationError("SvnFileSystem does not support move")

    #def walk(self, top, topdown=True):
    #    raise NoDefinedOperationError("SvnFileSystem does not support walk")

    def exists(self, path):
        try:
            return self.info(path).kind != pysvn.node_kind.none
        except pysvn.ClientError:
            return False

    def isfile(self, path):
        try:
            return self.info(path).kind == pysvn.node_kind.file
        except pysvn.ClientError:
            return False

    def isdir(self, path):
        try:
            return self.info(path).kind == pysvn.node_kind.dir
        except pysvn.ClientError:
            return False

    def log_by_time(self, path, start_time=None, stop_time=None):
        # let's start with head
        assert start_time > stop_time
        def accessor(revision_number):
            p = URI(path.uri, revision_number=revision_number)
            return p.info.last_changed_date

        highest_revision=path.info.last_changed_revision_number
        rn_start = min(
            binsearch(start_time, accessor, highest_revision, 1),
            highest_revision
            )
        rn_end = binsearch(stop_time, accessor, highest_revision, 1)
        revision_start = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            rn_start
            )
        revision_end = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            rn_end
            )
        with self.lock:
            result = self.client.log(
                path.uri,
                revision_start = revision_start,
                revision_end = revision_end,
                discover_changed_paths = True
                )

        return [LogEntry(x) for x in result]

        return []

    def open(self, path, options):
        """
        we want to support reading a single file from remote repository
        as a convenience method.
        The remote file will be exported the the local filesystem.
        After closing the filehandle, the local tempfile is removed.
        """
        assert options is None or options == 'r', options
        tmp_file_name = tempfile.mktemp()
        if self.revision_number is not None:
            self.client.export(
                path.uri,
                tmp_file_name,
                recurse=False,
                revision=self.revision_number
                )
        else:
            self.client.export(
                path.uri,
                tmp_file_name,
                recurse=False
                )
        return TempFileHandle(tmp_file_name)

    def log(self, path, revision_end_number=0):
        if self.revision_number is None:
            revision_start = pysvn.Revision(
                pysvn.opt_revision_kind.head
                )
        else:
            revision_start = self.revision_number
        revision_end = pysvn.Revision(
            pysvn.opt_revision_kind.number,
            revision_end_number
            )

        with self.lock:
            result = self.client.log(
                path.uri,
                revision_start = revision_start,
                revision_end = revision_end,
                discover_changed_paths = True
                )

        return [LogEntry(x) for x in result]

    def info(self, path):
        with self.lock:
            if self.revision_number:
                info_list = self.client.info2(
                    path.uri,
                    self.revision_number,
                    recurse=False
                    )
            else:
                info_list = self.client.info2(
                    path.uri,
                    recurse=False
                    )
        if info_list:
            obj = Bunch(info_list[0][1].items())
            obj.revision_number = obj.rev.number
            del obj['rev']
            obj.last_changed_revision_number = obj.last_changed_rev.number
            del obj['last_changed_rev']
            obj.last_changed_date = datetime.datetime.fromtimestamp(
                obj.last_changed_date
                )
            return obj
        else:
            return Bunch()


class SvnLocalFileSystem(SvnFileSystem):

    def info(self, path):
        info_obj = self.client.info(path.path)
        if info_obj is not None:
            obj = Bunch(info_obj.items())
            obj.revision_number = obj.revision.number
            del obj['revision']
            obj.last_changed_revision_number = obj.commit_revision.number
            del obj['commit_revision']
            obj.last_changed_date = datetime.datetime.fromtimestamp(
                obj.commit_time
                )
            del obj['commit_time']
            return obj
        else:
            return Bunch()

    def update(self, path):
        return self.client.update(path.path)

    def copy(self, other, options='', **argd):
        raise NotImplemtedError
