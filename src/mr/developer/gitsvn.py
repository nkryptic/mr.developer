from mr.developer import common
import os
import subprocess


logger = common.logger


class GitSvnError(common.WCError):
    pass


class GitSvnWorkingCopy(common.BaseWorkingCopy):
    def gitsvn_checkout(self, source, **kwargs):
        name = source['name']
        path = source['path']
        url = source['url']
        if os.path.exists(path):
            self.output((logger.info, "Skipped cloning of existing package '%s'." % name))
            return
        self.output((logger.info, "Cloning '%s' with git." % name))
        cmd = subprocess.Popen(["git", "svn", "clone", "--quiet", url, path],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSvnError("gitsvn cloning for '%s' failed.\n%s" % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout

    def gitsvn_update(self, source, **kwargs):
        name = source['name']
        path = source['path']
        self.output((logger.info, "Updating '%s' with gitsvn." % name))
        cmd = subprocess.Popen(["git", "svn", "rebase"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSvnError("gitsvn rebase for '%s' failed.\n%s" % (name, stderr))
        if kwargs.get('verbose', False):
            return stdout
    
    ### check for commits that haven't been pushed to svn
    def gitsvn_unpushed_commits(self, source):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git", "log", "--exit-code", "--pretty=oneline", "--abbrev-commit", "remotes/git-svn..HEAD"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        return bool(cmd.returncode != 0), stdout
    
    ### check for uncommitted changes
    def gitsvn_wc_changes(self, source):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git", "diff", "--exit-code", "--name-status", "HEAD"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        return bool(cmd.returncode != 0), stdout
    
    def gitsvn_confirm_on_master_branch(self, source):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git" "symbolic-ref", "HEAD"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        lines = stdout.strip().split('\n')
        return 'refs/heads/master' in lines
    
    def matches(self, source):
        name = source['name']
        path = source['path']
        cmd = subprocess.Popen(["git", "svn", "info"],
                               cwd=path,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        stdout, stderr = cmd.communicate()
        if cmd.returncode != 0:
            raise GitSvnError("gitsvn info for '%s' failed.\n%s" % (name, stderr))
        return (source['url'] in stdout.split())

    def checkout(self, source, **kwargs):
        name = source['name']
        path = source['path']
        update = self.should_update(source, **kwargs)
        if os.path.exists(path):
            if update:
                self.update(source, **kwargs)
            elif self.matches(source):
                self.output((logger.info, "Skipped checkout of existing package '%s'." % name))
            else:
                raise GitSvnError("Checkout URL for existing package '%s' differs. Expected '%s'." % (name, source['url']))
        else:
            return self.git_checkout(source, **kwargs)

    def update(self, source, **kwargs):
        name = source['name']
        path = source['path']
        if not self.matches(source):
            raise GitSvnError("Can't update package '%s', because it's URL doesn't match." % name)
        if self.status(source) != 'clean' and not kwargs.get('force', False):
            raise GitSvnError("Can't update package '%s', because it's dirty." % name)
        return self.git_update(source, **kwargs)
    
    def status(self, source, **kwargs):
        status = "clean"
        output = ""
        has_unpushed_commits, unpushed_commits_output = self.gitsvn_unpushed_commits(source)
        has_wc_changes, wc_changes_output = self.gitsvn_wc_changes(source)
        if has_unpushed_commits and has_wc_changes:
            status = "dirty and unpushed commits"
            output = "working copy status:\n%s\nunpushed commits:\n%s" % (wc_changes_output, unpushed_commits_output,)
        elif has_unpushed_commits:
            status = "unpushed commits"
            output = "unpushed commits:\n%s" % (unpushed_commits_output,)
        elif has_wc_changes:
            status = "dirty"
            output = "working copy status:\n%s" % (wc_changes_output)
        
        if kwargs.get('verbose', False):
            return status, output
        else:
            return status

common.workingcopytypes['gitsvn'] = GitSvnWorkingCopy
