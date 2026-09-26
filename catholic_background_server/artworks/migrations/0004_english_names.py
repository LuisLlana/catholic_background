# SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Renames the initial catalogue of celebrations and the groups from Spanish to English
in databases created with the first version. Celebrations renamed or added by the
users are not touched.
"""
from django.db import migrations

CELEBRATIONS = [
    ('Bautismo del Señor', 'Baptism of the Lord'),
    ('Miércoles de Ceniza', 'Ash Wednesday'),
    ('Domingo de Ramos en la Pasión del Señor', 'Palm Sunday of the Passion of the Lord'),
    ('Jueves Santo', 'Holy Thursday'),
    ('Viernes Santo de la Pasión del Señor', 'Good Friday of the Passion of the Lord'),
    ('Sábado Santo', 'Holy Saturday'),
    ('Domingo de Resurrección', 'Easter Sunday of the Resurrection of the Lord'),
    ('Domingo de la Divina Misericordia', 'Divine Mercy Sunday'),
    ('Ascensión del Señor', 'The Ascension of the Lord'),
    ('Pentecostés', 'Pentecost Sunday'),
    ('Bienaventurada Virgen María, Madre de la Iglesia', 'The Blessed Virgin Mary, Mother of the Church'),
    ('Jesucristo, Sumo y Eterno Sacerdote', 'Our Lord Jesus Christ, the Eternal High Priest'),
    ('Santísima Trinidad', 'The Most Holy Trinity'),
    ('Santísimo Cuerpo y Sangre de Cristo', 'The Most Holy Body and Blood of Christ'),
    ('Sagrado Corazón de Jesús', 'The Most Sacred Heart of Jesus'),
    ('Inmaculado Corazón de la Virgen María', 'The Immaculate Heart of the Blessed Virgin Mary'),
    ('Jesucristo, Rey del Universo', 'Our Lord Jesus Christ, King of the Universe'),
    ('Primer domingo de Adviento', 'First Sunday of Advent'),
    ('Sagrada Familia de Jesús, María y José', 'The Holy Family of Jesus, Mary and Joseph'),
    ('Santa María, Madre de Dios', 'Mary, the Holy Mother of God'),
    ('San Basilio Magno y san Gregorio Nacianceno', 'Saints Basil the Great and Gregory Nazianzen'),
    ('Santísimo Nombre de Jesús', 'The Most Holy Name of Jesus'),
    ('Epifanía del Señor', 'The Epiphany of the Lord'),
    ('San Raimundo de Peñafort', 'Saint Raymond of Penyafort'),
    ('San Antonio, abad', 'Saint Anthony, Abbot'),
    ('San Fructuoso, san Augurio y san Eulogio', 'Saints Fructuosus, Augurius and Eulogius'),
    ('San Sebastián', 'Saint Sebastian'),
    ('Santa Inés', 'Saint Agnes'),
    ('San Vicente, diácono', 'Saint Vincent, Deacon'),
    ('San Ildefonso', 'Saint Ildephonsus'),
    ('San Francisco de Sales', 'Saint Francis de Sales'),
    ('Conversión de san Pablo', 'The Conversion of Saint Paul the Apostle'),
    ('San Timoteo y san Tito', 'Saints Timothy and Titus'),
    ('Santo Tomás de Aquino', 'Saint Thomas Aquinas'),
    ('San Juan Bosco', 'Saint John Bosco'),
    ('Presentación del Señor', 'The Presentation of the Lord'),
    ('San Blas', 'Saint Blaise'),
    ('Santa Águeda', 'Saint Agatha'),
    ('San Pablo Miki y compañeros', 'Saint Paul Miki and Companions'),
    ('Santa Escolástica', 'Saint Scholastica'),
    ('Nuestra Señora de Lourdes', 'Our Lady of Lourdes'),
    ('San Cirilo y san Metodio, patronos de Europa', 'Saints Cyril and Methodius, Patrons of Europe'),
    ('Cátedra de san Pedro', 'The Chair of Saint Peter the Apostle'),
    ('San Policarpo', 'Saint Polycarp'),
    ('Santa Perpetua y santa Felicidad', 'Saints Perpetua and Felicity'),
    ('San Juan de Dios', 'Saint John of God'),
    ('San José, esposo de la Virgen María', 'Saint Joseph, Spouse of the Blessed Virgin Mary'),
    ('Anunciación del Señor', 'The Annunciation of the Lord'),
    ('San Isidoro de Sevilla', 'Saint Isidore of Seville'),
    ('San Jorge', 'Saint George'),
    ('San Marcos, evangelista', 'Saint Mark, Evangelist'),
    ('Santa Catalina de Siena, patrona de Europa', 'Saint Catherine of Siena, Patron of Europe'),
    ('San José Obrero', 'Saint Joseph the Worker'),
    ('San Atanasio', 'Saint Athanasius'),
    ('San Felipe y Santiago, apóstoles', 'Saints Philip and James, Apostles'),
    ('Nuestra Señora de Fátima', 'Our Lady of Fatima'),
    ('San Matías, apóstol', 'Saint Matthias, Apostle'),
    ('San Isidro Labrador', 'Saint Isidore the Farmer'),
    ('San Felipe Neri', 'Saint Philip Neri'),
    ('San Fernando', 'Saint Ferdinand'),
    ('Visitación de la Virgen María', 'The Visitation of the Blessed Virgin Mary'),
    ('San Justino', 'Saint Justin'),
    ('San Carlos Lwanga y compañeros', 'Saint Charles Lwanga and Companions'),
    ('San Bonifacio', 'Saint Boniface'),
    ('San Bernabé, apóstol', 'Saint Barnabas, Apostle'),
    ('San Antonio de Padua', 'Saint Anthony of Padua'),
    ('Natividad de san Juan Bautista', 'The Nativity of Saint John the Baptist'),
    ('San Ireneo', 'Saint Irenaeus'),
    ('San Pedro y san Pablo, apóstoles', 'Saints Peter and Paul, Apostles'),
    ('Santo Tomás, apóstol', 'Saint Thomas, Apostle'),
    ('San Benito, patrono de Europa', 'Saint Benedict, Patron of Europe'),
    ('Nuestra Señora del Carmen', 'Our Lady of Mount Carmel'),
    ('Santa María Magdalena', 'Saint Mary Magdalene'),
    ('Santa Brígida, patrona de Europa', 'Saint Bridget, Patron of Europe'),
    ('Santiago, apóstol, patrono de España', 'Saint James, Apostle, Patron of Spain'),
    ('San Joaquín y santa Ana', 'Saints Joachim and Anne'),
    ('Santa Marta, santa María y san Lázaro', 'Saints Martha, Mary and Lazarus'),
    ('San Ignacio de Loyola', 'Saint Ignatius of Loyola'),
    ('San Alfonso María de Ligorio', 'Saint Alphonsus Liguori'),
    ('San Juan María Vianney', 'Saint John Vianney'),
    ('Transfiguración del Señor', 'The Transfiguration of the Lord'),
    ('Santo Domingo de Guzmán', 'Saint Dominic'),
    ('Santa Teresa Benedicta de la Cruz, patrona de Europa', 'Saint Teresa Benedicta of the Cross, Patron of Europe'),
    ('San Lorenzo, diácono', 'Saint Lawrence, Deacon'),
    ('Santa Clara', 'Saint Clare'),
    ('Asunción de la Virgen María', 'The Assumption of the Blessed Virgin Mary'),
    ('San Bernardo', 'Saint Bernard'),
    ('San Pío X', 'Saint Pius X'),
    ('Santa María Virgen, Reina', 'The Queenship of the Blessed Virgin Mary'),
    ('San Bartolomé, apóstol', 'Saint Bartholomew, Apostle'),
    ('Santa Mónica', 'Saint Monica'),
    ('San Agustín', 'Saint Augustine'),
    ('Martirio de san Juan Bautista', 'The Passion of Saint John the Baptist'),
    ('San Gregorio Magno', 'Saint Gregory the Great'),
    ('Natividad de la Virgen María', 'The Nativity of the Blessed Virgin Mary'),
    ('San Juan Crisóstomo', 'Saint John Chrysostom'),
    ('Exaltación de la Santa Cruz', 'The Exaltation of the Holy Cross'),
    ('Nuestra Señora de los Dolores', 'Our Lady of Sorrows'),
    ('San Cornelio y san Cipriano', 'Saints Cornelius and Cyprian'),
    ('San Mateo, apóstol y evangelista', 'Saint Matthew, Apostle and Evangelist'),
    ('San Pío de Pietrelcina', 'Saint Pius of Pietrelcina'),
    ('San Vicente de Paúl', 'Saint Vincent de Paul'),
    ('San Miguel, san Gabriel y san Rafael, arcángeles', 'Saints Michael, Gabriel and Raphael, Archangels'),
    ('San Jerónimo', 'Saint Jerome'),
    ('Santa Teresa del Niño Jesús', 'Saint Therese of the Child Jesus'),
    ('Santos Ángeles Custodios', 'The Holy Guardian Angels'),
    ('San Francisco de Asís', 'Saint Francis of Assisi'),
    ('Nuestra Señora del Rosario', 'Our Lady of the Rosary'),
    ('Nuestra Señora del Pilar', 'Our Lady of the Pillar'),
    ('Santa Teresa de Jesús', 'Saint Teresa of Jesus'),
    ('San Ignacio de Antioquía', 'Saint Ignatius of Antioch'),
    ('San Lucas, evangelista', 'Saint Luke, Evangelist'),
    ('San Juan Pablo II', 'Saint John Paul II'),
    ('San Simón y san Judas, apóstoles', 'Saints Simon and Jude, Apostles'),
    ('Todos los Santos', 'All Saints'),
    ('Conmemoración de todos los fieles difuntos', 'The Commemoration of All the Faithful Departed'),
    ('San Carlos Borromeo', 'Saint Charles Borromeo'),
    ('Dedicación de la basílica de Letrán', 'The Dedication of the Lateran Basilica'),
    ('San León Magno', 'Saint Leo the Great'),
    ('San Martín de Tours', 'Saint Martin of Tours'),
    ('San Josafat', 'Saint Josaphat'),
    ('Santa Isabel de Hungría', 'Saint Elizabeth of Hungary'),
    ('Presentación de la Virgen María', 'The Presentation of the Blessed Virgin Mary'),
    ('Santa Cecilia', 'Saint Cecilia'),
    ('San Andrés Dung-Lac y compañeros', 'Saint Andrew Dung-Lac and Companions'),
    ('San Andrés, apóstol', 'Saint Andrew, Apostle'),
    ('San Francisco Javier', 'Saint Francis Xavier'),
    ('San Ambrosio', 'Saint Ambrose'),
    ('Inmaculada Concepción de la Virgen María', 'The Immaculate Conception of the Blessed Virgin Mary'),
    ('Nuestra Señora de Guadalupe', 'Our Lady of Guadalupe'),
    ('Santa Lucía', 'Saint Lucy'),
    ('San Juan de la Cruz', 'Saint John of the Cross'),
    ('Natividad del Señor', 'The Nativity of the Lord'),
    ('San Esteban, protomártir', 'Saint Stephen, the First Martyr'),
    ('San Juan, apóstol y evangelista', 'Saint John, Apostle and Evangelist'),
    ('Santos Inocentes, mártires', 'The Holy Innocents, Martyrs'),
]
GROUPS = [("Editores", "Editors"), ("Revisores", "Reviewers")]


def rename(apps, schema_editor, forward=True):
    db = schema_editor.connection.alias
    Celebration = apps.get_model("artworks", "Celebration")
    Group = apps.get_model("auth", "Group")
    for spanish, english in CELEBRATIONS:
        old, new = (spanish, english) if forward else (english, spanish)
        Celebration.objects.using(db).filter(name=old).update(name=new)
    for spanish, english in GROUPS:
        old, new = (spanish, english) if forward else (english, spanish)
        if not Group.objects.using(db).filter(name=new).exists():
            Group.objects.using(db).filter(name=old).update(name=new)


def backwards(apps, schema_editor):
    rename(apps, schema_editor, forward=False)


class Migration(migrations.Migration):
    dependencies = [("artworks", "0003_english_labels"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(rename, backwards)]
