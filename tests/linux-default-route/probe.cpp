#include <QCoreApplication>
#include <QDebug>
#include <QNetworkInterface>
#include <QPair>
#include <QScopeGuard>
#include <QString>
#include <arpa/inet.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <net/if.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cstring>
#include <iostream>
#include <chrono>
#include <dirent.h>

QPair<QString, QNetworkInterface> gateway()
{
#include GATEWAY_BODY
}

int fdCount()
{
    DIR *dir = opendir("/proc/self/fd");
    int count = 0;
    while (readdir(dir)) ++count;
    closedir(dir);
    return count;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QString expectedGateway = argc > 1 ? argv[1] : "10.254.254.1";
    const QString expectedInterface = argc > 2 ? argv[2] : "test0";
    const int repetitions = argc > 3 ? std::stoi(argv[3]) : 1;
    const auto start = std::chrono::steady_clock::now();
    const int before = fdCount();
    QPair<QString, QNetworkInterface> result;
    bool correct = true;
    for (int i = 0; i < repetitions; ++i) {
        result = gateway();
        correct &= result.first == expectedGateway && result.second.name() == expectedInterface;
    }
    const int leaked = fdCount() - before;
    std::cout << "gateway=" << result.first.toStdString()
              << " interface=" << result.second.name().toStdString()
              << " leaked_fds=" << leaked << " repetitions=" << repetitions
              << " seconds=" << std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count()
              << std::endl;
    return correct && leaked == 0 ? 0 : 1;
}
