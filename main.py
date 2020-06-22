# reset wifi. Somehow the memory of what was set in mqtt_as prevents connecting again otherwise.
import network
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)
sta_if.active(False)
ap_if.active(False)


try:
    from clients import client_br
except ImportError:
    try:
        from clients import client_lr
    except ImportError:
        try:
            from clients import client_roof
        except ImportError:
            raise ImportError('no client to import')
        else:
            client_roof.run()
    else:
        client_lr.run()
else:
    client_br.run()
