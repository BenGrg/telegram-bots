from telegram import Update
from telegram.ext import CallbackContext
import os
import imagehash
import shutil
from git import Repo
from PIL import Image
import requests
import random


class MemeHandler(object):

    def __init__(self, path_git_rot, git_url):
        self.path_git = path_git_rot
        self.git_url = git_url
        # GIT INIT
        self.repo = Repo(path_git_rot)
        assert not self.repo.bare
        self.repo.config_reader()  # get a config reader for read-only access
        with self.repo.config_writer():  # get a config writer to change configuration
            pass  # call release() to be sure changes are written and locks are released
        assert not self.repo.is_dirty()  # check the dirty state

    def __download_image(self, update: Update, context: CallbackContext):
        image = context.bot.getFile(update.message.photo[-1])
        file_id = str(image.file_id)
        print("file_id: " + file_id)
        img_path = self.path_git + '/memesFolder/' + file_id + ".png"
        image.download(img_path)
        return img_path

    # return true if all went well and image wasn't already present, False otherwise
    def add_meme(self, update: Update, context: CallbackContext):
        tmp_path = self.__download_image(update, context)
        img_hash = self.__calculate_hash(tmp_path)
        is_present = self.__check_file_already_present(img_hash)
        if not is_present:
            filename = img_hash + '.jpg'
            self.__copy_file_to_git_meme_folder(tmp_path, filename)
            self.__add_file_to_git(filename)
            return True
        else:
            return False

    def get_url_meme(self):
        contents = requests.get(self.git_url).json()
        potential_memes = []
        for file in contents:
            if 'png' in file['name'] or 'jpg' in file['name'] or 'jpeg' in file['name'] or 'mp4' in file['name']:
                potential_memes.append(file['download_url'])
        url = random.choice(potential_memes)
        return url

    def __copy_file_to_git_meme_folder(self, path, hash_with_extension):
        shutil.copyfile(path, self.path_git + '/memesFolder/' + hash_with_extension)

    def __calculate_hash(self, path_to_image):
        return str(imagehash.average_hash(Image.open(path_to_image)))

    def __add_file_to_git(self, filename):
        index = self.repo.index
        index.add(self.path_git + "/memesFolder/" + filename)
        index.commit("adding dank meme " + filename)
        origin = self.repo.remote('origin')
        origin.push(force=True)

    # Returns True if the file is already present in the MEME_GIT_REPO directory
    def __check_file_already_present(self, meme_hash):
        found = False
        for file in os.listdir(self.path_git + '/memesFolder/'):
            filename = os.fsdecode(file)
            filename_no_extension = filename.split(".")[0]
            if filename_no_extension == meme_hash:
                found = True
        return found

    # REMOVE MEME
    def delete_meme(self, update: Update, context: CallbackContext, password_shouldbe):
        query_received = update.message.text.split(' ')
        if len(query_received) == 3:
            print("someone wants to delete a meme")
            password = query_received[1]
            if password == password_shouldbe:
                print("password correct")
                to_delete = query_received[2]
                if self.__check_file_already_present(to_delete):
                    print("meme found")
                    filename = to_delete + '.jpg'
                    index = self.repo.index
                    index.remove(self.path_git + "/memesFolder/" + filename)
                    index.commit("adding dank meme " + filename)
                    origin = self.repo.remote('origin')
                    origin.push(force=True)
                    os.remove(self.path_git + "/memesFolder/" + filename)
                    print("deleting meme " + to_delete)
                    chat_id = update.message.chat_id
                    context.bot.send_message(chat_id=chat_id, text="removed" + filename)
