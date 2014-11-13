#!/usr/bin/python3
import praw
import requests
import re
import sys
import time
import os
import glob
import CycleModRecs as cmr
import datetime

logBuf = ""
logTimeStamp = ""
searchResult = ""

USERNAME            = "username"
PASSWORD            = "password"
SUBREDDIT           = "boibtest"
USER_AGENT          = "CycleModRecsCtrl by /u/boib"
CYCLE_FREQ_MINUTES  = 1
BLURB_TAG           = "#####"
MODRECPOOL          = "modrecpool"
IMAGENAME           = "CurrentModRec.png"
CURRENT_BOOK_FILE   = "CurrentBookIndex.txt"
HELP_MSG            =   "To communicate with the cycle mod rec bot:\n\n"+\
                        "1.  Be a /r/books moderator\n\n"+\
                        "2.  Put \"modrecs\" in the subject line\n\n"+\
                        "3.  Issue one of the following commands\n\n"+\
                        "* stop                         \n\n"+\
                        "* start                        \n\n"+\
                        "* help (this message)          \n\n"+\
                        "* get status                   \n\n"+\
                        "* get next book                \n\n"+\
                        "* get previous book            \n\n"+\
                        "* get all books by moderator   \n\n"+\
                        "* get all books by author      \n\n"+\
                        "* get book by title            \n\n"+\
                        "* set next book index          \n\n"+\
                        "* set next book title          \n\n"+\
                        "* jump to next book now        \n\n"+\
                        "* jump to index now            \n\n"+\
                        "* jump to title now            \n\n"+\
                        "* add book                     \n\n"+\
                        "* delete book                  \n\n"+\
                        "* edit book                    \n\n"+\
                        "For extended help, send the command \"help <command>\"\n\n"



#####################################################################
def DEBUG(s, start=False, stop=False):

    global logBuf
    global logTimeStamp

    print (s)

    logBuf = logBuf + s + "\n\n"
    if stop:
        r.submit("bookbotlog", logTimeStamp, text=logBuf)
        logBuf = ""


#####################################################################


def doReplies (replies, searchStr):
    global searchResult

    for reply in replies:
        if re.search(searchStr, reply.body, re.I):
            #print ("https://www.reddit.com/message/messages/" + reply.parent_id[3:])
            searchResult += "https://www.reddit.com/message/messages/" + reply.parent_id[3:] + "\n\n"
            return True

        if reply.replies:
            if doReplies(reply.replies, searchStr):
                return True

    return False


def searchModMail (r,s,m):
    #
    # r=reddit, s=msgbody, m=msgC:\Users\sds\python\CycleModRecsCtrl.pyauthor
    #
    global searchResult


    searchStr = s.strip()
    returnBuf = "Searching for **%s**\n\n" % searchStr
    searchResult = ""

    try:
        inbox = r.get_mod_mail(subreddit='books', limit=1000)

        if not inbox:
            returnBuf += "aint got no messages\n\n"
        else:
            for inboxMsg in inbox:
                if inboxMsg.replies:
                    doReplies(inboxMsg.replies, searchStr)


    except Exception as e:
        returnBuf += 'An error has occured: %s ' % (e)

    if not searchResult:
        returnBuf += "Did not find **%s**" % searchStr
    else:
        returnBuf += searchResult

    return returnBuf



def getBookList (r):

    nextBook = 0
    #
    # get the "modrecpool" wiki page
    #
    sr = r.get_subreddit(SUBREDDIT)
    mrp = sr.get_wiki_page(MODRECPOOL)

    try:
        f = open(CURRENT_BOOK_FILE, "r")
        nextBook = int(f.readline()) + 1
        f.close()
    except:
        nextBook = 0;

    DEBUG("cycleBooks: next book index = %d" % nextBook)

    #
    # get the list of mod rec books
    #
    mrps = mrp.content_md.split("{Book}")
    bookList = []
    for i in mrps:
        i = i.strip()
        myBook = cmr.decodeBook(i)
        if myBook:
            bookList.append(myBook)


    numBooks = len(bookList)
    DEBUG("found %s books" % numBooks)
    if len(bookList) < 2:
        DEBUG("only %s books -- looks like an error" % numBooks)

    # if we're at the end, start over from top
    if nextBook >= numBooks:
        nextBook = 0;

    DEBUG("\nfound current book **%s** at index:%s out of %s" % (bookList[nextBook]['title'], nextBook, numBooks))
    return (bookList, nextBook)




def stopCycle():
    print ("stopCycle()")
    return("stopCycle()")

def addSched(r,s,m):
    print ("addSched()")

    returnBuf = ""

    msgLines = s.splitlines()

    for b in msgLines:

        if b.startswith('imageurl:'):
            imageurl = b[len('imageurl:'):].strip()

        if b.startswith('blurburl:'):
            blurburl = b[len('blurburl:'):].strip()

        if b.startswith('author:'):
            author = b[len('author:'):].strip()

        if b.startswith('title:'):
            title = b[len('title:'):].strip()

        if b.startswith('date:'):
            scheddate = b[len('date:'):].strip()

        if b.startswith('banner:'):
            banner = b[len('banner:'):].strip()

        if b.startswith('time:'):
            amatime = b[len('time:'):].strip()



    if not blurburl or not imageurl or not author or not scheddate:
        returnBuf += "Error decoding msg (%s)\n\n" % s
    else:

        # error if 'date' already in schedule
        inSched = glob.glob("sched/" + scheddate + "*")
        if inSched:
            returnBuf += "Error: **%s** is already in the schedule.  You must delete it first before adding another item for the same date\n\n" % inSched[0]
        else:
            try:
                if not amatime:
                    amatime = ""
                else:
                    amatime = " at " + amatime

                year, month, day = (int(x) for x in scheddate.split('-'))
                weekday = datetime.date(year, month, day).strftime("%A")

                banner =  "%s%s, AMA with **%s**, author of ***%s***" % (weekday, amatime, author, title)

                filename = scheddate + '-' + author.replace(' ', '.')
                f = open("sched/" + filename, 'w')
                f.write("imageurl: " + imageurl + "\n")
                f.write("blurburl: " + blurburl + "\n")
                f.write("banner: " + banner + "\n")
                f.close()

                returnBuf += "**" + filename + "** added to the schedule\n\n"
            except:
                returnBuf += "Error adding %s to the schedule" % filename

    return returnBuf



def delSched(r,s,m):
    print ("delSched()")

    returnBuf = ""

    msgLines = s.splitlines()

    for b in msgLines:

        if b.startswith('date:'):
            scheddate = b[len('date:'):].strip()

    if not scheddate:
        returnBuf += "Error decoding msg (%s)\n\n" % s
    else:

        inSched = glob.glob("sched/" + scheddate + "*")
        if inSched:
            try:
                os.remove(inSched[0])
                returnBuf += "**%s** deleted" % inSched[0]
            except:
                returnBuf += "Error deleting **%s**" % inSched[0]
        else:
            returnBuf += "Error: Nothing exists in the schedule for **%s**" % scheddate


    return returnBuf



def getSched(r,s,m):
    print ("getSched()")
    returnBuf = ""

    schedDir = os.listdir("sched/")
    for sf in schedDir:
        returnBuf += sf + "\n\n"

    return(returnBuf)

def startCycle():
    print ("startCycle()")
    return ("startCycle()")

def help(r,s,m):
    print ("help()")
    return ("help()")
def getCurrentBook(r,s,m):
    print ("status()")
    return ("status()")
def getNextBook(r, s, m):
    print ("getNextBook()")

    foundBooks  = 0
    returnBuf   = "get next book: \n\n"
    (bookList, currentBook) = getBookList (r)
    if currentBook == len(bookList)-1:
        nextBook = 0
    else:
        nextBook = currentBook + 1

    try:
        returnBuf += bookList[nextBook]['title'] + " by " + bookList[nextBook]['author']
    except:
        pass

    return returnBuf

def getPrevBook(r, s, m):
    print ("getPrevBook()")

    foundBooks  = 0
    returnBuf   = "get prev book: \n\n"
    (bookList, currentBook) = getBookList (r)
    if currentBook == 0:
        prevBook = len(bookList) - 1
    else:
        prevBook = currentBook - 1

    try:
        returnBuf += bookList[prevBook]['title'] + " by " + bookList[prevBook]['author']
    except:
        pass

    return returnBuf


def getAllByMod(r, s, m):
    print ("getAllByMod(%s)" % s)

    foundBooks  = 0
    returnBuf   = ""
    booksByMod  = []
    bookList = getBookList (r)
    for i in bookList:
        if s == i['moderator']:
            returnBuf += i['title'] + " by " + i['author'] + "\n\n"
            foundBooks += 1

    returnBuf = "get all by mod: Found " + str(foundBooks) + " books by " + s + "\n\n---\n\n" + returnBuf
    return returnBuf

def getAllByAuthor(r, s, m):
    print ("getAllByAuthor()")

    foundBooks  = 0
    returnBuf   = ""
    booksByMod  = []
    bookList = getBookList (r)
    for i in bookList:
        mObj = re.search(s, i['author'], re.I)
        if mObj:
            returnBuf += i['title'] + " by " + i['author'] + "\n\n"
            foundBooks += 1

    returnBuf = "get all by author: Found " + str(foundBooks) + " books by " + s + "\n\n---\n\n" + returnBuf
    return returnBuf


def getBookInfoByTitle(r,s,m):
    print ("getBookInfoByTitle()")
    return ("getBookInfoByTitle()")
def setNextBookByIndex(r,s,m):
    print ("setNextBookByIndex()")
    return ("setNextBookByIndex()")
def setNextBookByTitle(r,s,m):
    print ("setNextBookByTitle()")
    return ("setNextBookByTitle()")
def jumpToNextBookNow(r,s,m):
    print ("jumpToNextBookNow()")
    return ("jumpToNextBookNow()")
def jumpToIndexNow(r,s,m):
    print ("jumpToIndexNow()")
    return ("jumpToIndexNow()")
def jumpToTitleNow(r,s,m):
    print ("jumpToTitleNow()")
    return ("jumpToTitleNow()")


def addBook(r, s, m):
    print ("addBook()")

    # 1) parse string, make sure title and imageurl exist
    # 2) get current book list and current displayed book
    # 3) make sure title is not already in list
    # 4) save book locally in "new books" list, make sure it doesn't already exist
    # 5) when cycle time comes, check new book list first and:
    #   a) add it to the list web page (modrecpool)
    #   b) jump to that book

    (bookList, currentBook) = getBookList (r)
    newBookList = getNewBookList()
    saveNewList = False

    rawbooks = s.split("{Book}")
    booksToAdd = []
    for i in rawbooks:
        oldfound = False
        newfound = False
        i = i.strip()
        myBook = cmr.decodeBook(i)
        if myBook:
            # check if book being added is already in the book list
            for existingBook in bookList:
                if existingBook['title'] == myBook['title']:
                    oldfound = True
                    returnBuf += "ERROR: " + existingBook['title'] + " by " + existingBook['author'] + " is alread in the list\n\n"

            # if the book being added isnt already in the new list, add it
            if not oldfound:
                for newBook in newBookList:
                    if newBook['title'] == myBook['title']:
                        newfound = True
                        returnBuf += "ERROR: " + newBook['title'] + " by " + newBook['author'] + " is alread in the 'NEW' list\n\n"

                if not newfound:
                    newBookList.append(myBook)
                    saveNewList = True
                    returnBuf += "Adding " + newBook['title'] + " by " + newBook['author'] + " to the 'NEW' list\n\n"


    if saveNewList:
        saveNewList(newBookList)



def deleteBook(r, s, m):
    print ("deleteBook()")
    return ("deleteBook()\n\n*Not Implemented Yet*\n\n")
def editBook(r, s, m):
    print ("editBook()")
    return ("editBook()\n\n**NOT IMPLEMENTED YET**\n\n")


def changeImage (r,s,m):

    #
    # do an AMA image
    # 1) download image from link
    #    a) verify scale is 163x260 and a PNG, scale and convert if not
    # 2) upload image to stylesheet
    # 3) update name in stylesheet
    # 4) update blurb
    #
    # data passed in s:
    #   image url, worldcat url
    #

    blurburl = ""
    imgurl = ""
    returnBuf = ""

    bookarray = s.splitlines()

    for x in bookarray:
        mObj = re.search("imageurl:(.*)", x, re.I)
        if mObj:
            imgurl = mObj.group(1).strip()
        else:
            print ("error getting imageurl (%s)" % x)

        mObj = re.search("blurburl:(.*)", x, re.I)
        if mObj:
            blurburl = mObj.group(1).strip()
        else:
            print ("error getting blurburl (%s)" % x)


    if not blurburl or not imgurl:
        returnBuf += "Error decoding msg (%s)\n\n" % s

    else:
        if not cmr.downloadImage(imgurl, IMAGENAME):
            returnBuf += "ama() Error downloading %s\n\n" % imgurl
        else:
            try:
                cmr.uploadImage (sr, IMAGENAME)
                cmr.updateBlurb(sr, blurburl, "")
                cmr.updateBookImageName (sr, IMAGENAME)
                returnBuf += "Success!\n\n"
            except Exception as e:
                returnBuf += 'An error has occured: %s\n\n' % e

    return returnBuf

##############################################################################



if __name__=='__main__':
    #
    # init and log into reddit
    #

    if len(sys.argv) != 2:
        print ("Please provide subreddit on cmd line: <CycleModRecsCtrl.py> <subreddit name>")
        quit()

    if sys.argv[1] != "books" and sys.argv[1] != "boibtest":
        print ("books or boibtest, please")
        quit()

    SUBREDDIT = sys.argv[1]
    CURRENT_BOOK_FILE   = "CrntBookIndx-" + SUBREDDIT + ".txt"

    cmr.setDebug(DEBUG)

    print("==============================")
    r = cmr.init()
    cmr.login(r, USERNAME, PASSWORD)
    print("==============================")


    commands = {
        "changeimage":      changeImage,
        "getcurrentbook":   getCurrentBook,
        "getnextbook":      getNextBook,
        "getprevbook":      getPrevBook,
        "addsched":         addSched,
        "delsched":         delSched,
        "getsched":         getSched,
        "searchModMail":    searchModMail,
    }



    sr = r.get_subreddit(SUBREDDIT)
    mods = sr.get_moderators()

    while True:
        time.sleep(30)
        try:
            inbox = r.get_unread(limit=300)

            if not inbox:
                print ("aint got no messages")
            else:
                msg = HELP_MSG

                for inboxMsg in inbox:
                    isMod = False
                    error = False
                    cmd = ""
                    subred = ""
                    logTimeStamp = "cmrc - /r/" + SUBREDDIT + " - " + time.strftime("%d%b%Y-%H:%M:%S")

                    DEBUG("Msg **%s** from **%s**" % (inboxMsg.subject, inboxMsg.author.name))

                    #
                    # did the msg come from a moderator?
                    #
                    for mod in mods:
                        if mod.name == inboxMsg.author.name:
                            isMod = True
                            break

                    if not isMod:
                        msg = "*I am a bot* and I only talk to /r/books moderators."
                        error = True

                    #
                    # did they send the cmd and subreddit in the subject field?
                    #
                    if not error:
                        try:
                            cmd, subred = inboxMsg.subject.split()
                        except:
                            pass

                        if not cmd or not subred:
                            msg = "unknown cmd: (%s) " % inboxMsg.subject.strip()
                            error = True

                    #
                    # is the subreddit valid?
                    #
                    if not error:
                        if subred != 'books' and subred != "boibtest":
                            msg = "invalid subreddit: " + subred
                            error = True

                    #
                    # if the cmd is valid, execute!
                    #
                    if not error:
                        if cmd in commands:
                            msg = commands[cmd](r, inboxMsg.body, inboxMsg.author.name)
                            #DEBUG("Reply to (%s):\n\n%s" % (inboxMsg.author.name, msg), stop=True)
                        else:
                            msg = "unknown cmd: (%s) (%s) " % (cmd, subred)

                    #
                    # log it, reply to sender, mark it read
                    #
                    DEBUG(msg, stop=True)
                    inboxMsg.reply(msg)
                    inboxMsg.mark_as_read()


        except Exception as e:
            DEBUG('An error has occured: %s ' % (e))
            continue




