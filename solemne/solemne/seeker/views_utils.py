import json
from solemne.utils import ErrHandle, is_ajax
from solemne.seeker.models import get_crpp_date, get_current_datetime, \
   Action, STYPE_IMPORTED, STYPE_EDITED, STYPE_MANUAL

def solemne_action_add(view, instance, details, actiontype):
    """User can fill this in to his/her liking"""

    oErr = ErrHandle()
    try:
        # Check if this needs processing
        stype_edi_fields = getattr(view, "stype_edi_fields", None)
        if stype_edi_fields and not instance is None:
            # Get the username: 
            username = view.request.user.username
            # Process the action
            cls_name = instance.__class__.__name__
            Action.add(username, cls_name, instance.id, actiontype, json.dumps(details))

            # -------- DEBGGING -------
            # print("solemne_action_add type={}".format(actiontype))
            # -------------------------

            # Check the details:
            if 'changes' in details:
                changes = details['changes']
                if 'stype' not in changes or len(changes) > 1:
                    # Check if the current STYPE is *not* 'Edited*
                    stype = getattr(instance, "stype", "")
                    if stype != STYPE_EDITED:
                        bNeedSaving = False
                        key = ""
                        if 'model' in details:
                            bNeedSaving = details['model'] in stype_edi_fields
                        if not bNeedSaving:
                            # We need to do stype processing, if any of the change fields is in [stype_edi_fields]
                            for k,v in changes.items():
                                if k in stype_edi_fields:
                                    bNeedSaving = True
                                    key = k
                                    break

                        if bNeedSaving:
                            # Need to set the stype to EDI
                            instance.stype = STYPE_EDITED
                            # Adapt status note
                            snote = json.loads(instance.snote)
                            snote.append(dict(date=get_crpp_date(get_current_datetime()), username=username, status=STYPE_EDITED, reason=key))
                            instance.snote = json.dumps(snote)
                            # Save it
                            instance.save()
    except:
        msg = oErr.get_error_message()
        oErr.DoError("solemne_action_add")
    # Now we are ready
    return None

def solemne_get_history(instance):
    lhtml= []
    lhtml.append("<table class='table'><thead><tr><td><b>User</b></td><td><b>Date</b></td><td><b>Description</b></td></tr></thead><tbody>")
    # Get the history for this item
    lHistory = Action.get_history(instance.__class__.__name__, instance.id)
    for obj in lHistory:
        description = ""
        if obj['actiontype'] == "new":
            description = "Create New"
        elif obj['actiontype'] == "add":
            description = "Add"
        elif obj['actiontype'] == "delete":
            description = "Delete"
        elif obj['actiontype'] == "change":
            description = "Changes"
        elif obj['actiontype'] == "import":
            description = "Import Changes"
        if 'changes' in obj:
            lchanges = []
            for key, value in obj['changes'].items():
                lchanges.append("<b>{}</b>=<code>{}</code>".format(key, value))
            changes = ", ".join(lchanges)
            if 'model' in obj and obj['model'] != None and obj['model'] != "":
                description = "{} {}".format(description, obj['model'])
            description = "{}: {}".format(description, changes)
        lhtml.append("<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(obj['username'], obj['when'], description))
    lhtml.append("</tbody></table>")

    sBack = "\n".join(lhtml)
    return sBack


