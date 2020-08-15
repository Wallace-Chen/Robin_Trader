import imaplib, email
from email.header import decode_header
import dateutil.parser
import datetime as dt
import re
import time
from dateutil import tz

user = ''
password = ''
imap_url = 'imap.gmail.com'


# Function to search for a key value pair
def search(key, value, con):
    result, data = con.search(None, key, '"{}"'.format(value))
    return data

# Function to get the list of emails under this label
def get_emails(result_bytes, con):
    msgs = [] # all the email data are pushed inside an array
    for num in result_bytes[0].split():
        typ, data = con.fetch(num, '(RFC822)')
        for response in data:
            body_msg = ""
            item = {}
            if isinstance(response, tuple):
                # parse a bytes email into a message object
                msg = email.message_from_bytes(response[1])
                # decode the email subject
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    # if it's a bytes, decode to str
                    subject = subject.decode()
                # email sender
                from_ = msg.get("From")
                if "Your Email Verification Code" not in subject: continue
                item["subject"] = subject
                item["from"] = from_
                time = msg["Date"]
                dt = dateutil.parser.parse(time)
                item["date"] = dt
                #item["date"] = dt.astimezone(dateutil.tz.tzlocal()).strftime('%a, %b %d, %Y at %I:%M %p')
                # if the email message is multipart
                if msg.is_multipart():	
                    # iterate over email parts
                    for part in msg.walk():
                        # extract content type of email
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            # get the email body
                            body = part.get_payload(decode=True).decode()
                            if content_type == "text/plain" and "attachment" not in content_disposition: body_msg = body_msg + body
                        except:
                            pass
#                        if content_type == "text/plain" and "attachment" not in content_disposition:
#                            pass
                            # print text/plain emails and skip attachments
							#print(body)
                else:
                    print("single part!\n")
                    # extract content type of email
                    content_type = msg.get_content_type()
                    # get the email body
                    body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        # print only text email parts
                        body_msg = body
						#print(body)
#                print(body_msg)
                item["body"] = body_msg
                msgs.append(item)
    return msgs

def email_code(msgs, now):
    if not msgs: return None
    msg = msgs[-1]
    date = msg["date"]
    date = date.astimezone(tz.tzlocal())
    body = msg["body"]
    match = re.search(r'\d{6}', body, re.M|re.I)
    delta = time.mktime(date.timetuple()) - time.mktime(now.timetuple())
    if(abs(int(delta)) < 300 ): return match.group()
    return None


def getcode():
    now = dt.datetime.now()
    try:
        time.sleep(6)
        # this is done to make SSL connnection with GMAIL 
        con = imaplib.IMAP4_SSL(imap_url)  
  
        # logging the user in 
        con.login(user, password)  
        
        retry = 0
  
        # calling function to check for email under this label 
        con.select('Inbox')  
  
        # fetching emails from this user "tu**h*****1@gmail.com" 
        msgs = get_emails(search('FROM', 'notifications@robinhood.com', con), con)

        code = email_code(msgs, now)
        while retry < 6 and code == None:
            retry += 1
            con.select('Inbox')
            msgs = get_emails(search('FROM', 'notifications@robinhood.com', con), con)
            code = email_code(msgs, now)
            time.sleep(10)
        print("code: {}\n".format(code))
        return code
#    print(email.message_from_string(str(msgs[-1][0])))
#    print(get_body(msgs))
    except Exception as e:
        print(e)
        return None

