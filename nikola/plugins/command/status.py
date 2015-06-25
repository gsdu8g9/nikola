# -*- coding: utf-8 -*-

# Copyright © 2012-2015 Roberto Alsina and others.

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function
import io
import os
from datetime import datetime
from dateutil.tz import gettz, tzlocal

from nikola.plugin_categories import Command


class CommandDeploy(Command):
    """ Site status. """
    name = "status"

    doc_purpose = "display site status"
    doc_description = "Show information about the posts and site deployment."
    logger = None
    cmd_options = [
        {
            'name': 'list_drafts',
            'short': 'd',
            'long': 'list-drafts',
            'type': bool,
            'default': False,
            'help': 'List all drafts',
        },
        {
            'name': 'list_modified',
            'short': 'm',
            'long': 'list-modified',
            'type': bool,
            'default': False,
            'help': 'List all modified files since last deployment',
        },
        {
            'name': 'list_scheduled',
            'short': 's',
            'long': 'list-scheduled',
            'type': bool,
            'default': False,
            'help': 'List all scheduled posts',
        },
    ]

    def _execute(self, options, args):

        self.site.scan_posts()

        timestamp_path = os.path.join(self.site.config["CACHE_FOLDER"], "lastdeploy")

        last_deploy = None

        try:
            with io.open(timestamp_path, "r", encoding="utf8") as inf:
                last_deploy = datetime.strptime(inf.read().strip(), "%Y-%m-%dT%H:%M:%S.%f")
                last_deploy_offset = datetime.utcnow() - last_deploy
        except (IOError, Exception):
            print("It does not seem like you’ve ever deployed the site (or cache missing).")

        if last_deploy:

            fmod_since_deployment = []
            for root, dirs, files in os.walk(self.site.config["OUTPUT_FOLDER"], followlinks=True):
                if not dirs and not files:
                    continue
                for fname in files:
                    fpath = os.path.join(root, fname)
                    fmodtime = datetime.fromtimestamp(os.stat(fpath).st_mtime)
                    if fmodtime.replace(tzinfo=tzlocal()) > last_deploy.replace(tzinfo=gettz("UTC")).astimezone(tz=tzlocal()):
                        fmod_since_deployment.append(fpath)

            if len(fmod_since_deployment) > 0:
                print("{0} output files modified since last deployment {1} ago.".format(str(len(fmod_since_deployment)), self.human_time(last_deploy_offset)))
                if options['list_modified']:
                    for fpath in fmod_since_deployment:
                        print("Modified: '{0}'".format(fpath))
            else:
                print("Last deployment {0} ago.".format(self.human_time(last_deploy_offset)))

        now = datetime.utcnow().replace(tzinfo=gettz("UTC"))

        posts_count = len(self.site.all_posts)

        # find all drafts
        posts_drafts = [post for post in self.site.all_posts if post.is_draft]
        posts_drafts = sorted(posts_drafts, key=lambda post: post.source_path)

        # find all scheduled posts with offset from now until publishing time
        posts_scheduled = [(post.date - now, post) for post in self.site.all_posts if post.publish_later]
        posts_scheduled = sorted(posts_scheduled, key=lambda offset_post: (offset_post[0], offset_post[1].source_path))

        if len(posts_scheduled) > 0:
            if options['list_scheduled']:
                for offset, post in posts_scheduled:
                    print("Scheduled: '{1}' ({2}; source: {3}) in {0}".format(self.human_time(offset), post.meta('title'), post.permalink(), post.source_path))
            else:
                offset, post = posts_scheduled[0]
                print("{0} to next scheduled post ('{1}'; {2}; source: {3}).".format(self.human_time(offset), post.meta('title'), post.permalink(), post.source_path))
        if options['list_drafts']:
            for post in posts_drafts:
                print("Draft: '{0}' ({1}; source: {2})".format(post.meta('title'), post.permalink(), post.source_path))
        print("{0} posts in total, {1} scheduled, and {2} drafts.".format(posts_count, len(posts_scheduled), len(posts_drafts)))

    def human_time(self, dt):
        days = dt.days
        hours = dt.seconds / 60 // 60
        minutes = dt.seconds / 60 - (hours * 60)
        if days > 0:
            return "{0:.0f} days and {1:.0f} hours".format(days, hours)
        elif hours > 0:
            return "{0:.0f} hours and {1:.0f} minutes".format(hours, minutes)
        elif minutes:
            return "{0:.0f} minutes".format(minutes)
        return False
