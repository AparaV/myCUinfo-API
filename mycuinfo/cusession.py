#!/usr/bin/python
# coding=utf8
import requests


class CUSession(requests.sessions.Session):

    # get past the weird javascript redirects that mycuinfo uses to login
    def __init__(self, username, password):

        session = requests.Session()

        # get the inital page, found url by disecting js code from
        # mycuinfo.colorado.edu
        init_page = session.get("https://ping.prod.cu.edu/idp/startSSO.ping" +
                                "?PartnerSpId=SP:EnterprisePortal&IdpAdapte" +
                                "rId=BoulderIDP&TargetResource=https://port" +
                                "al.prod.cu.edu%2Fpsp%2Fepprod%2FUCB2%2FENT" +
                                "P%2Fh%2F%3Ftab%3DDEFAULT")
        init_text = init_page.text

        # set the post data for the next request
        resumePath = init_text.split('name="resumePath" value="')[
            1].split('"')[0]
        ver1_data = {
            "allowInteraction": "true",
            "resumePath": resumePath,
            "reauth": "false"
        }

        # human verification page num. 1
        post_page = session.post(
            "https://ping.prod.cu.edu/proxy/?cmd=idp-sso", data=ver1_data)
        post_page_text = post_page.text

        SAMLRequest = post_page_text.split(
            'name="SAMLRequest" value="')[1].split('"')[0]
        RelayState = post_page_text.split(
            'name="RelayState" value="')[1].split('"')[0]
        ver2_data = {
            "SAMLRequest": SAMLRequest,
            "RelayState": RelayState
        }

        # human verification page num. 2
        second_post_page = session.post("https://fedauth.colorado.edu/idp/" +
                                        "profile/SAML2/POST/SSO",
                                        data=ver2_data)
        second_post_page_text = second_post_page.text

        postURL = second_post_page_text.split(
            'fm-login" name="login" action="')[1].split('"')[0]
        login_data = {
            "timezoneOffset": "0",
            "_eventId_proceed": "Log In",
            "j_username": username,
            "j_password": password
        }

        # user login page
        login_request = session.post(
            "https://fedauth.colorado.edu" + postURL, data=login_data)

        login_text = login_request.text

        RelayState = login_text.split('name="RelayState" value="')[
            1].split('"')[0]
        SAMLResponse = login_text.split(
            'name="SAMLResponse" value="')[1].split('"')[0]

        ver3_data = {
            "RelayState": RelayState,
            "SAMLResponse": SAMLResponse
        }

        # human verification page num. 3
        third_post_page = session.post(
            "https://ping.prod.cu.edu/sp/ACS.saml2",
            data=ver3_data)

        third_post_page_text = third_post_page.text

        REF = third_post_page_text.split('name="REF" value="')[1].split('"')[0]
        TargetResource = (third_post_page_text.split(
            'name="TargetResource" value="')[1].split('"')[0])
        ver4_data = {
            "REF": REF,
            "TargetResource": TargetResource
        }

        # human verification page num. 4
        URL = third_post_page_text.split('method="post" action="')[
            1].split('"')[0]
        forth_post_page = session.post(URL, data=ver4_data)

        forth_post_page_text = forth_post_page.text

        RelayState = forth_post_page_text.split(
            'name="RelayState" value="')[1].split('"')[0]
        SAMLResponse = forth_post_page_text.split(
            'name="SAMLResponse" value="')[1].split('"')[0]

        ver5_data = {
            "RelayState": RelayState,
            "SAMLResponse": SAMLResponse
        }

        # human verification page num. 5
        fifth_post_page = session.post("https://ping.prod.cu.edu/sp/ACS.saml2",
                                       data=ver5_data)

        # if the user/pass was bad, the url will not be correct
        if fifth_post_page.url != "https://portal.prod.cu.edu/psp/epprod/UCB2/ENTP/h/?tab=DEFAULT":
            self.valid = False
        else:
            self.valid = True

        # from here on, we are a regular user who has all the logged in cookies
        # we can do anything that a web user could (javascript not included)
        self.session = session

        # cached data
        self.__cached_info = None
        self.__cached_classes = {}
        self.__cached_books = {}
        self.__cached_gpa = None

    # get the basic info of the user (name, student ID, Major, College, etc.)
    def info(self, force=False):

        # try retrieving cached data
        if self.__cached_info is None or force:

            # if the user is not logged in, error out, else go for it
            if self.valid == False:
                return False

            # set the url (break it up so the line isnt huge)
            url0 = "https://portal.prod.cu.edu/psp/epprod/UCB2/ENTP/h/?cmd=get"
            url1 = "CachedPglt&pageletname=ISCRIPT_CU_PROFILE_V2"
            url = url0 + url1

            # get the page
            pageLoad = self.session.get(url)

            # get the text (encode it unicode)
            pageText = pageLoad.text

            # split the text up a few times till we just have the info
            splitText = pageText.split("<!--")[1][:-2].strip().split("\n")[2:-5]

            # create a blank dictonary to add to
            info = {}

            # Each item will be formatted like <name>value</name> or <name>
            # Only items like the former will be added
            for item in splitText:
                name = item.split('<')[1].split('>')[0]
                value = item.split('>')[1].split('<')[0]
                if value != "":
                    info[name] = value

            self.__cached_info = info

        return self.__cached_info

    def classes(self, term="Spring 2017", force=False):

        # check if data exists
        if term in self.__cached_classes.keys():
            found = True
        else:
            found = False

        # try retrieving cached data
        if not found or force:

            # if the user is not logged in, error out, else go for it
            if self.valid == False:
                return False

            # split up the url so it fits on one line
            url0 = "https://portal.prod.cu.edu/psp/epprod/UCB2/ENTP/h/"
            url1 = "?cmd=getCachedPglt&pageletname=CU_STUDENT_SCHEDULE"
            url = url0 + url1

            # get the page text
            pageText = self.session.get(url).text

            # split up the first part by the Course Schedule
            try:
                fallText = pageText.split("Grades / Details: " + term)[1].split(
                    "* FCQ = Faculty Course Questionnaire")[0]
            except:
                print("Invalid term given for classes. Valid Ex: 'Fall 2015'")
                return None

            classInfoList = fallText.split("<tr>")[2:]

            classList = []

            for classInfo in classInfoList:

                # a lot of html parsing and spliting. Really hard to leave a nice
                # context without looking at the html. Tried to write so things
                # won't get wonky if values are blank

                tempClass = {}

                courseSection = classInfo[5:].split("&nbsp;")

                if len(courseSection) == 1:
                    continue

                nameAndType = classInfo.split('<th')[1].split(
                    '>')[1].split('<')[0]
                nameAndType = nameAndType.split('&nbsp;')
                tempClass["name"] = nameAndType[0]
                tempClass["type"] = nameAndType[1][1:-1]
                classInfo = classInfo.split('</th>')[1]

                courseInfo = classInfo.split('<td>')[1].split('<br')[0]

                tempClass["department"] = courseInfo[0:4]
                courseInfo = courseInfo.split('-')
                tempClass["classCode"] = courseInfo[0][-4:]
                tempClass["section"] = courseInfo[1]
                classInfo = classInfo.split('</td>')[1:]

                dateAndTime = classInfo[0].split("meetingtime\"")[1][
                    1:].split("</div>")[0].split(">")

                tempClass["days"] = dateAndTime[0].split("<")[0][:-1]
                tempClass["startTime"] = dateAndTime[1].split("<")[0]
                tempClass["endTime"] = dateAndTime[3].split("<")[0]

                tempInstructor = {}

                # Some courses don't have an instructor listed
                try:
                    instructorInfo = classInfo[1].split("meetingtime\"")[1][
                        1:].split("</div>")[0].split(">")

                    instrutr = instructorInfo[0].split("&nbsp;")[0].split(" ")

                    tempInstructor["firstName"] = instrutr[1]
                    tempInstructor["lastName"] = instrutr[0]
                except:
                    tempInstructor["firstName"] = "Staff"
                    tempInstructor["lastName"] = ""

                tempClass["instructor"] = tempInstructor

                tempClass["credits"] = int(classInfo[3].split(">")[1])
                tempClass["status"] = classInfo[4].split(">")[1]
                tempClass["grade"] = classInfo[5].split(">")[1]

                if tempClass["grade"] == "":
                    del(tempClass["grade"])

                classList.append(tempClass)

            self.__cached_classes[term] = classList

        return self.__cached_classes[term]

    # look up the books needed for any class
    def books(self, Department, CourseNumber, Section,
                term="Fall2015", force=False):

        # check if data exists
        key = term + Department + str(CourseNumber) + str(Section)
        if key in self.__cached_books.keys():
            found = True
        else:
            found = False

        # try retrieving cached data
        if not found or force:

            # if the user is not logged in, error out, else go for it
            if self.valid == False:
                return False

            # set the term info, we made it a little nicer becuase CU uses nums to
            # set the term info. The move up by three/four every semester, so we can
            # use that forumual to change the term info to correct number for the
            # API.
            if term == "Fall2015" or term == 2147:
                term = "2157"
            elif term == "Spring2015" or term == 2151:
                term = "2151"
            elif term == "Summer2015" or term == 2154:
                term = "2154"
            elif term == 2167:
                term = "2167"
            else:
                raise Exception("Error: Invalid Term")

            # simple check to see if the department is valid
            if len(Department) != 4:
                raise Exception("Error: Invalid Department")

            # simple check to see if Course Number is valid
            if len(CourseNumber) != 4:
                raise Exception("Error: Invalid CourseNumber")

            # simple check to see if Section Number is valid
            if len(Section) != 3:
                raise Exception("Error: Invalid Section (DO included leading 0s)")

            # now that all the check are there, we can start trying to get books

            # set the base url (split so the line isnt huge)
            baseUrl0 = "https://portal.prod.cu.edu/psc/epprod/UCB2/ENTP/s/WEBLIB_CU"
            baseUrl1 = "_SCHED.ISCRIPT1.FieldFormula.IScript_Get_Boulder_Books?"
            baseUrl = baseUrl0 + baseUrl1

            # set the inputs based on the method inputs
            course1 = "&course1=" + Department + CourseNumber
            section1 = "&section1=" + Section
            term1 = "&term1=" + term

            # we set a variable called session1, I have always found it to equal B
            session1 = "&session1=B"

            pageText = self.session.get(
                baseUrl + course1 + section1 + term1 + session1).text
            bookList = []

            bookInfoList = pageText.split("<tbody>")[1].split(
                "</tbody>")[0].split("<tr>")[1:]

            for bookInfo in bookInfoList:

                infoList = bookInfo.split("<td")
                tempBook = {}

                # gets all the book info, adds nothing is something errors
                try:
                    tempBook["author"] = infoList[1][1:-6]
                    tempBook["title"] = infoList[2][1:-6]
                    tempBook["required"] = infoList[3].split(">")[1][:-4]
                    tempBook["course"] = infoList[4][1:-6].replace('\n', "")
                    tempBook["isbn"] = infoList[5][1:-12]

                    bookList.append(tempBook)
                except:
                    pass

            self.__cached_books[key] = bookList

        return self.__cached_books[key]

    # look up overall GPA
    def GPA(self, force=False):

        # try retrieving cached data
        if self.__cached_gpa is None or force:

            # set the url (broken up for line length)
            url0 = "https://isis-cs.prod.cu.edu/psc/csprod/UCB2/HRMS/c/"
            url1 = "SA_LEARNER_SERVICES.SSR_SSENRL_GRADE.GBL?"
            url2 = "ACAD_CAREER=UGRD&INSTITUTION=CUBLD&STRM=2151"
            baseUrl = url0 + url1 + url2

            # get the page text
            pageText = self.session.post(baseUrl).text

            # get the GPA
            splitText = pageText.split("PSEDITBOXLABEL")[-1].split(">")[1][:5]

            self.__cached_gpa = float(splitText)

        return self.__cached_gpa
