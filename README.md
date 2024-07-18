# epub-to-cbz

# 功能
- 将epub转为cbz
- 提取epub中的元数据，写入cbz文件中的ComicInfo.xml，可以被komga，kavita识别
- 读取spine对image进行重命名,image或xhtml的文件名混乱，也能正确排序
- .opf文件中存在而epub中不存在的文件会被忽略
